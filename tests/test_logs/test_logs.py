import boto3
import os
import sure  # noqa
import six
from botocore.exceptions import ClientError

from moto import mock_logs, settings
from nose.tools import assert_raises
from nose import SkipTest

_logs_region = "us-east-1" if settings.TEST_SERVER_MODE else "us-west-2"


@mock_logs
def test_log_group_create():
    conn = boto3.client("logs", "us-west-2")
    log_group_name = "dummy"
    response = conn.create_log_group(logGroupName=log_group_name)

    response = conn.describe_log_groups(logGroupNamePrefix=log_group_name)
    assert len(response["logGroups"]) == 1
    # AWS defaults to Never Expire for log group retention
    assert response["logGroups"][0].get("retentionInDays") == None

    response = conn.delete_log_group(logGroupName=log_group_name)


@mock_logs
def test_exceptions():
    conn = boto3.client("logs", "us-west-2")
    log_group_name = "dummy"
    log_stream_name = "dummp-stream"
    conn.create_log_group(logGroupName=log_group_name)
    with assert_raises(ClientError):
        conn.create_log_group(logGroupName=log_group_name)

    # descrine_log_groups is not implemented yet

    conn.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)
    with assert_raises(ClientError):
        conn.create_log_stream(
            logGroupName=log_group_name, logStreamName=log_stream_name
        )

    conn.put_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        logEvents=[{"timestamp": 0, "message": "line"}],
    )

    with assert_raises(ClientError):
        conn.put_log_events(
            logGroupName=log_group_name,
            logStreamName="invalid-stream",
            logEvents=[{"timestamp": 0, "message": "line"}],
        )


@mock_logs
def test_put_logs():
    conn = boto3.client("logs", "us-west-2")
    log_group_name = "dummy"
    log_stream_name = "stream"
    conn.create_log_group(logGroupName=log_group_name)
    conn.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)
    messages = [
        {"timestamp": 0, "message": "hello"},
        {"timestamp": 0, "message": "world"},
    ]
    putRes = conn.put_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name, logEvents=messages
    )
    res = conn.get_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name
    )
    events = res["events"]
    nextSequenceToken = putRes["nextSequenceToken"]
    assert isinstance(nextSequenceToken, six.string_types) == True
    assert len(nextSequenceToken) == 56
    events.should.have.length_of(2)


@mock_logs
def test_filter_logs_interleaved():
    conn = boto3.client("logs", "us-west-2")
    log_group_name = "dummy"
    log_stream_name = "stream"
    conn.create_log_group(logGroupName=log_group_name)
    conn.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)
    messages = [
        {"timestamp": 0, "message": "hello"},
        {"timestamp": 0, "message": "world"},
    ]
    conn.put_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name, logEvents=messages
    )
    res = conn.filter_log_events(
        logGroupName=log_group_name, logStreamNames=[log_stream_name], interleaved=True
    )
    events = res["events"]
    for original_message, resulting_event in zip(messages, events):
        resulting_event["eventId"].should.equal(str(resulting_event["eventId"]))
        resulting_event["timestamp"].should.equal(original_message["timestamp"])
        resulting_event["message"].should.equal(original_message["message"])


@mock_logs
def test_filter_logs_raises_if_filter_pattern():
    if os.environ.get("TEST_SERVER_MODE", "false").lower() == "true":
        raise SkipTest("Does not work in server mode due to error in Workzeug")
    conn = boto3.client("logs", "us-west-2")
    log_group_name = "dummy"
    log_stream_name = "stream"
    conn.create_log_group(logGroupName=log_group_name)
    conn.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)
    messages = [
        {"timestamp": 0, "message": "hello"},
        {"timestamp": 0, "message": "world"},
    ]
    conn.put_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name, logEvents=messages
    )
    with assert_raises(NotImplementedError):
        conn.filter_log_events(
            logGroupName=log_group_name,
            logStreamNames=[log_stream_name],
            filterPattern='{$.message = "hello"}',
        )


@mock_logs
def test_put_retention_policy():
    conn = boto3.client("logs", "us-west-2")
    log_group_name = "dummy"
    response = conn.create_log_group(logGroupName=log_group_name)

    response = conn.put_retention_policy(logGroupName=log_group_name, retentionInDays=7)

    response = conn.describe_log_groups(logGroupNamePrefix=log_group_name)
    assert len(response["logGroups"]) == 1
    assert response["logGroups"][0].get("retentionInDays") == 7

    response = conn.delete_log_group(logGroupName=log_group_name)


@mock_logs
def test_delete_retention_policy():
    conn = boto3.client("logs", "us-west-2")
    log_group_name = "dummy"
    response = conn.create_log_group(logGroupName=log_group_name)

    response = conn.put_retention_policy(logGroupName=log_group_name, retentionInDays=7)

    response = conn.describe_log_groups(logGroupNamePrefix=log_group_name)
    assert len(response["logGroups"]) == 1
    assert response["logGroups"][0].get("retentionInDays") == 7

    response = conn.delete_retention_policy(logGroupName=log_group_name)

    response = conn.describe_log_groups(logGroupNamePrefix=log_group_name)
    assert len(response["logGroups"]) == 1
    assert response["logGroups"][0].get("retentionInDays") == None

    response = conn.delete_log_group(logGroupName=log_group_name)


@mock_logs
def test_get_log_events():
    conn = boto3.client("logs", "us-west-2")
    log_group_name = "test"
    log_stream_name = "stream"
    conn.create_log_group(logGroupName=log_group_name)
    conn.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)

    events = [{"timestamp": x, "message": str(x)} for x in range(20)]

    conn.put_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name, logEvents=events
    )

    resp = conn.get_log_events(
        logGroupName=log_group_name, logStreamName=log_stream_name, limit=10
    )

    resp["events"].should.have.length_of(10)
    resp.should.have.key("nextForwardToken")
    resp.should.have.key("nextBackwardToken")
    resp["nextForwardToken"].should.equal(
        "f/00000000000000000000000000000000000000000000000000000010"
    )
    resp["nextBackwardToken"].should.equal(
        "b/00000000000000000000000000000000000000000000000000000000"
    )
    for i in range(10):
        resp["events"][i]["timestamp"].should.equal(i)
        resp["events"][i]["message"].should.equal(str(i))

    next_token = resp["nextForwardToken"]

    resp = conn.get_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        nextToken=next_token,
        limit=10,
    )

    resp["events"].should.have.length_of(10)
    resp.should.have.key("nextForwardToken")
    resp.should.have.key("nextBackwardToken")
    resp["nextForwardToken"].should.equal(
        "f/00000000000000000000000000000000000000000000000000000020"
    )
    resp["nextBackwardToken"].should.equal(
        "b/00000000000000000000000000000000000000000000000000000000"
    )
    for i in range(10):
        resp["events"][i]["timestamp"].should.equal(i + 10)
        resp["events"][i]["message"].should.equal(str(i + 10))

    resp = conn.get_log_events(
        logGroupName=log_group_name,
        logStreamName=log_stream_name,
        nextToken=resp["nextBackwardToken"],
        limit=10,
    )

    resp["events"].should.have.length_of(10)
    resp.should.have.key("nextForwardToken")
    resp.should.have.key("nextBackwardToken")
    for i in range(10):
        resp["events"][i]["timestamp"].should.equal(i)
        resp["events"][i]["message"].should.equal(str(i))


@mock_logs
def test_list_tags_log_group():
    conn = boto3.client("logs", "us-west-2")
    log_group_name = "dummy"
    tags = {"tag_key_1": "tag_value_1", "tag_key_2": "tag_value_2"}

    response = conn.create_log_group(logGroupName=log_group_name)
    response = conn.list_tags_log_group(logGroupName=log_group_name)
    assert response["tags"] == {}

    response = conn.delete_log_group(logGroupName=log_group_name)
    response = conn.create_log_group(logGroupName=log_group_name, tags=tags)
    response = conn.list_tags_log_group(logGroupName=log_group_name)
    assert response["tags"] == tags

    response = conn.delete_log_group(logGroupName=log_group_name)


@mock_logs
def test_tag_log_group():
    conn = boto3.client("logs", "us-west-2")
    log_group_name = "dummy"
    tags = {"tag_key_1": "tag_value_1"}
    response = conn.create_log_group(logGroupName=log_group_name)

    response = conn.tag_log_group(logGroupName=log_group_name, tags=tags)
    response = conn.list_tags_log_group(logGroupName=log_group_name)
    assert response["tags"] == tags

    tags_with_added_value = {"tag_key_1": "tag_value_1", "tag_key_2": "tag_value_2"}
    response = conn.tag_log_group(
        logGroupName=log_group_name, tags={"tag_key_2": "tag_value_2"}
    )
    response = conn.list_tags_log_group(logGroupName=log_group_name)
    assert response["tags"] == tags_with_added_value

    tags_with_updated_value = {"tag_key_1": "tag_value_XX", "tag_key_2": "tag_value_2"}
    response = conn.tag_log_group(
        logGroupName=log_group_name, tags={"tag_key_1": "tag_value_XX"}
    )
    response = conn.list_tags_log_group(logGroupName=log_group_name)
    assert response["tags"] == tags_with_updated_value

    response = conn.delete_log_group(logGroupName=log_group_name)


@mock_logs
def test_untag_log_group():
    conn = boto3.client("logs", "us-west-2")
    log_group_name = "dummy"
    response = conn.create_log_group(logGroupName=log_group_name)

    tags = {"tag_key_1": "tag_value_1", "tag_key_2": "tag_value_2"}
    response = conn.tag_log_group(logGroupName=log_group_name, tags=tags)
    response = conn.list_tags_log_group(logGroupName=log_group_name)
    assert response["tags"] == tags

    tags_to_remove = ["tag_key_1"]
    remaining_tags = {"tag_key_2": "tag_value_2"}
    response = conn.untag_log_group(logGroupName=log_group_name, tags=tags_to_remove)
    response = conn.list_tags_log_group(logGroupName=log_group_name)
    assert response["tags"] == remaining_tags

    response = conn.delete_log_group(logGroupName=log_group_name)
