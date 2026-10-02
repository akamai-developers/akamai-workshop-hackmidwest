"""Knowledge: chunking, batching, the bucket reader, and sync, with boto3 and the embeddings client mocked."""
from types import SimpleNamespace as NS
from unittest import mock

from agent import config, knowledge
from agent.memory import LocalMemory

CFG = config.Config(
    base_url="http://fake/v1", api_key="hk_test",
    obj_endpoint="https://us-sea-1.linodeobjects.com", obj_bucket="hackmidwest-test",
    obj_access_key="AK", obj_secret_key="SK",
)


class FakeEmbeddings:
    """Gives each text a vector that points toward the topic words it contains."""

    TOPICS = ["park", "food", "judg", "wifi"]

    def __init__(self):
        self.requests = []
        self.embeddings = NS(create=self.create)

    def create(self, model, input):
        self.requests.append(list(input))
        return NS(data=[NS(embedding=self.vector(text)) for text in input])

    def vector(self, text):
        text = text.lower()
        return [1.0 + text.count(topic) * 5 if topic in text else 0.1 for topic in self.TOPICS]


class FakeSource:
    def __init__(self, files):
        self.files_now = dict(files)  # key -> (version, text)
        self.reads = []

    def files(self):
        return {key: version for key, (version, _) in self.files_now.items()}

    def read(self, key):
        self.reads.append(key)
        return self.files_now[key][1]


def make_knowledge(files):
    client = FakeEmbeddings()
    embed = knowledge.Embedder(CFG, client=client)
    source = FakeSource(files)
    return knowledge.Knowledge(source, LocalMemory(), embed, "live", "test"), source, client


def test_chunk_keeps_paragraphs_together_and_splits_long_ones():
    text = "\n\n".join(["one two three", "four five", "six seven eight nine ten eleven"])
    assert knowledge.chunk(text, size=5) == ["one two three four five", "six seven eight nine ten", "eleven"]
    assert knowledge.chunk("", size=5) == []
    long = " ".join(f"w{i}" for i in range(1200))
    assert [len(c.split()) for c in knowledge.chunk(long)] == [500, 500, 200]


def test_batches_respect_the_endpoint_limits():
    short = ["word"] * 40
    assert [len(b) for b in knowledge.batches(short)] == [16, 16, 8]
    big = [" ".join(["w"] * 500)] * 16  # 8,000 words: over the token budget in one request
    sizes = [sum(len(t.split()) for t in b) for b in knowledge.batches(big)]
    assert all(size <= knowledge.BATCH_WORDS for size in sizes)
    assert sum(sizes) == 8000


def test_embedder_batches_and_uses_the_cache_for_single_texts():
    client = FakeEmbeddings()
    cache = mock.Mock()
    cache.get_vector.side_effect = [None, [9.0, 9.0, 9.0, 9.0]]
    embed = knowledge.Embedder(CFG, cache=cache, client=client)

    assert len(embed([f"text {i}" for i in range(20)])) == 20
    assert [len(r) for r in client.requests] == [16, 4]

    first = embed.one("where to park")  # cache miss: one request, then stored
    second = embed.one("where to park")  # cache hit: no request
    assert first == client.vector("where to park")
    assert second == [9.0, 9.0, 9.0, 9.0]
    assert len(client.requests) == 3
    cache.set_vector.assert_called_once_with("hackathon-embedding", "where to park", first)


def test_sync_indexes_new_files_and_search_finds_the_right_one():
    kn, source, _ = make_knowledge({
        "parking.md": ("v1", "Park in Lot C. Parking is free with a badge."),
        "food.md": ("v1", "Food is in the atrium. Lunch is at noon."),
    })
    assert kn.sync() == 2
    hits = kn.search("Where can I park the car?")
    assert hits[0].key == "parking.md"
    assert "Lot C" in hits[0].text


def test_sync_skips_unchanged_files_reindexes_changed_ones_and_forgets_deleted_ones():
    kn, source, client = make_knowledge({
        "parking.md": ("v1", "Park in Lot C."),
        "food.md": ("v1", "Food is in the atrium."),
    })
    kn.sync()
    requests_after_first_sync = len(client.requests)

    assert kn.sync() == 0  # nothing changed: no reads, no embedding requests
    assert len(client.requests) == requests_after_first_sync

    source.files_now["parking.md"] = ("v2", "Park in Lot D now.")
    del source.files_now["food.md"]
    assert kn.sync() == 1
    assert kn.memory.document_keys() == {"parking.md"}
    assert "Lot D" in kn.search("parking")[0].text


def test_search_with_an_empty_bucket_returns_nothing():
    kn, _, _ = make_knowledge({})
    assert kn.search("Where can I park?") == []


def test_bucket_lists_only_text_files_with_their_etags():
    s3 = mock.Mock()
    s3.get_paginator.return_value.paginate.return_value = [
        {"Contents": [{"Key": "parking.md", "ETag": '"a"'}, {"Key": "logo.png", "ETag": '"b"'}]},
        {"Contents": [{"Key": "notes.TXT", "ETag": '"c"'}]},
        {},
    ]
    with mock.patch("boto3.client", return_value=s3) as client:
        bucket = knowledge.Bucket(CFG)
    assert bucket.files() == {"parking.md": '"a"', "notes.TXT": '"c"'}
    kwargs = client.call_args.kwargs
    assert kwargs["endpoint_url"] == "https://us-sea-1.linodeobjects.com"
    assert kwargs["region_name"] == "us-sea-1"
    assert bucket.where == "bucket hackmidwest-test at us-sea-1.linodeobjects.com"


def test_a_broken_bucket_does_not_stop_the_agent():
    s3 = mock.Mock()
    s3.get_paginator.return_value.paginate.side_effect = RuntimeError("InvalidAccessKeyId")
    with mock.patch("boto3.client", return_value=s3):
        kn = knowledge.connect(CFG, LocalMemory(), knowledge.Embedder(CFG, client=FakeEmbeddings()))
    assert kn.state == "error"
    assert "InvalidAccessKeyId" in kn.detail


def test_without_a_bucket_the_agent_reads_the_sample_folder():
    cfg = config.Config(base_url="http://fake/v1", api_key="hk_test")
    kn = knowledge.connect(cfg, LocalMemory(), knowledge.Embedder(cfg, client=FakeEmbeddings()))
    assert kn.state == "fallback"
    assert kn.memory.document_keys() == {"parking.md", "rules.md", "schedule.md"}
