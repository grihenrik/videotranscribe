import pytest
from app.utils.xml_parser import parse_xml_captions, convert_timestamp_to_srt, format_seconds_to_timestamp
from app.utils.file_manager import convert_to_srt, convert_to_vtt, ensure_srt_timestamp_format, convert_timestamp_to_vtt


# Test XML parsing
def test_parse_xml_captions():
    # Test TTML format
    xml_content = """
    <?xml version="1.0" encoding="utf-8"?>
    <tt xmlns="http://www.w3.org/ns/ttml">
      <body>
        <p begin="00:00:00.000" end="00:00:05.000">This is the first caption</p>
        <p begin="00:00:05.000" end="00:00:10.000">This is the second caption</p>
      </body>
    </tt>
    """
    
    captions = parse_xml_captions(xml_content)
    
    assert len(captions) == 2
    assert captions[0]["start"] == "00:00:00,000"
    assert captions[0]["end"] == "00:00:05,000"
    assert captions[0]["text"] == "This is the first caption"
    
    # Test YT format
    xml_content = """
    <?xml version="1.0" encoding="utf-8"?>
    <transcript>
      <text start="0" dur="5">This is the first caption</text>
      <text start="5" dur="5">This is the second caption</text>
    </transcript>
    """
    
    captions = parse_xml_captions(xml_content)
    
    assert len(captions) == 2
    assert captions[0]["text"] == "This is the first caption"
    
    # Test invalid XML
    with pytest.raises(ValueError):
        parse_xml_captions("This is not XML")


# Test timestamp conversion
def test_convert_timestamp_to_srt():
    # Test HH:MM:SS.mmm format
    assert convert_timestamp_to_srt("00:00:00.000") == "00:00:00,000"
    
    # Test seconds format
    assert convert_timestamp_to_srt("5.500") == "00:00:05,500"


# Test seconds to timestamp formatting
def test_format_seconds_to_timestamp():
    # Test integer seconds
    assert format_seconds_to_timestamp(5) == "00:00:05,000"
    
    # Test seconds with milliseconds
    assert format_seconds_to_timestamp(5.5) == "00:00:05,500"
    
    # Test minutes
    assert format_seconds_to_timestamp(65) == "00:01:05,000"
    
    # Test hours
    assert format_seconds_to_timestamp(3665) == "01:01:05,000"


# Test SRT conversion
def test_convert_to_srt():
    captions = [
        {"start": "00:00:00,000", "end": "00:00:05,000", "text": "This is the first caption"},
        {"start": "00:00:05,000", "end": "00:00:10,000", "text": "This is the second caption"}
    ]
    
    srt = convert_to_srt(captions)
    
    expected = (
        "1\n"
        "00:00:00,000 --> 00:00:05,000\n"
        "This is the first caption\n"
        "\n"
        "2\n"
        "00:00:05,000 --> 00:00:10,000\n"
        "This is the second caption\n"
    )
    
    assert srt == expected


# Test VTT conversion
def test_convert_to_vtt():
    captions = [
        {"start": "00:00:00,000", "end": "00:00:05,000", "text": "This is the first caption"},
        {"start": "00:00:05,000", "end": "00:00:10,000", "text": "This is the second caption"}
    ]
    
    vtt = convert_to_vtt(captions)
    
    expected = (
        "WEBVTT\n"
        "\n"
        "00:00:00.000 --> 00:00:05.000\n"
        "This is the first caption\n"
        "\n"
        "00:00:05.000 --> 00:00:10.000\n"
        "This is the second caption\n"
    )
    
    assert vtt == expected


# Test timestamp format conversion
def test_ensure_srt_timestamp_format():
    # Test SRT format
    assert ensure_srt_timestamp_format("00:00:00,000") == "00:00:00,000"
    
    # Test dot format
    assert ensure_srt_timestamp_format("00:00:00.000") == "00:00:00,000"
    
    # Test seconds format
    assert ensure_srt_timestamp_format("5.5") == "00:00:05,500"


# Test VTT timestamp conversion
def test_convert_timestamp_to_vtt():
    # Test SRT to VTT conversion
    assert convert_timestamp_to_vtt("00:00:00,000") == "00:00:00.000"
