from app.services.pdf_service import chunk_pages, extract_title_and_abstract


def test_chunk_pages_respects_size_and_overlap():
    page = " ".join(f"word{i}" for i in range(1000))
    chunks = chunk_pages([page], chunk_size_words=300, overlap_words=45)

    assert len(chunks) > 1
    # first chunk exactly chunk_size_words
    assert len(chunks[0].content.split()) == 300
    # consecutive chunks overlap: last N words of chunk[0] == first N of chunk[1] region
    words0 = chunks[0].content.split()
    words1 = chunks[1].content.split()
    assert words0[-45:] == words1[:45]


def test_chunk_pages_skips_empty_pages():
    chunks = chunk_pages(["", "   ", "real content here"], chunk_size_words=300, overlap_words=45)
    assert len(chunks) == 1
    assert chunks[0].page_number == 3


def test_chunk_pages_empty_input_returns_empty_list():
    assert chunk_pages([]) == []


def test_extract_title_and_abstract_finds_abstract_marker():
    pages = ["My Great Paper Title\nAbstract: this paper studies foo and bar in depth."]
    title, abstract = extract_title_and_abstract(pages)
    assert title == "My Great Paper Title"
    assert "foo and bar" in abstract


def test_extract_title_and_abstract_handles_no_pages():
    title, abstract = extract_title_and_abstract([])
    assert title == "Untitled"
    assert abstract == ""
