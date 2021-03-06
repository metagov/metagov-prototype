import base64
import hashlib
import hmac
import json
import logging

import metagov.core.plugin_decorators as Registry
import metagov.plugins.discourse.schemas as Schemas
import requests
from metagov.core.errors import PluginErrorInternal
from metagov.core.models import GovernanceProcess, Plugin, ProcessStatus

logger = logging.getLogger(__name__)

EVENT_POST_CREATED = "post_created"
EVENT_TOPIC_CREATED = "topic_created"


@Registry.plugin
class Discourse(Plugin):
    name = "discourse"
    config_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "api_key": {"type": "string"},
            "server_url": {"type": "string"},
            "webhook_secret": {"type": "string"},
            "webhook_slug": {"type": "string"},
        },
        "required": ["api_key", "server_url", "webhook_secret"],
    }
    events = [{"type": EVENT_POST_CREATED}, {"type": EVENT_TOPIC_CREATED}]

    class Meta:
        proxy = True

    def initialize(self):
        resp = requests.get(f"{self.config['server_url']}/about.json")
        response = resp.json()
        community_name = response.get("about").get("title")
        logger.info(f"Initialized Discourse plugin for community {community_name}")
        self.state.set("community_name", community_name)

    def construct_post_url(self, post):
        return f"{self.config['server_url']}/t/{post['topic_slug']}/{post['topic_id']}/{post['post_number']}"

    def construct_topic_url(self, topic):
        return f"{self.config['server_url']}/t/{topic['slug']}/{topic['id']}"

    def construct_post_response(self, post):
        return {"url": self.construct_post_url(post), "topic_id": post["topic_id"], "post_id": post["id"]}

    def discourse_request(self, method, route, username="system", json=None, data=None):
        url = f"{self.config['server_url']}/{route}"
        logger.info(f"{method} {url}")

        headers = {"Api-Username": username, "Api-Key": self.config["api_key"]}
        resp = requests.request(method, url, headers=headers, json=json, data=data)
        if not resp.ok:
            logger.error(f"{resp.status_code} {resp.reason}")
            logger.error(resp.request.body)
            # logger.error(resp.request.headers)
            raise PluginErrorInternal(resp.text)
        if resp.content:
            return resp.json()
        return None

    @Registry.action(
        slug="create-message",
        description="Start a new private message thread",
        input_schema=Schemas.send_message_parameters,
        output_schema=Schemas.create_post_or_topic_response,
    )
    def create_message(self, parameters):
        username = parameters.pop("initiator", "system")
        parameters["target_recipients"] = ",".join(parameters.pop("target_usernames"))
        parameters["archetype"] = "private_message"
        post = self.discourse_request("POST", "posts.json", username=username, json=parameters)
        return self.construct_post_response(post)

    @Registry.action(
        slug="create-post",
        description="Create a new post",
        input_schema=Schemas.create_post_parameters,
        output_schema=Schemas.create_post_or_topic_response,
    )
    def create_post(self, parameters):
        username = parameters.pop("initiator", "system")
        post = self.discourse_request("POST", "posts.json", username=username, json=parameters)
        return self.construct_post_response(post)

    @Registry.action(
        slug="create-topic",
        description="Create a new topic",
        input_schema=Schemas.create_topic_parameters,
        output_schema=Schemas.create_post_or_topic_response,
    )
    def create_topic(self, parameters):
        username = parameters.pop("initiator", "system")
        post = self.discourse_request("POST", "posts.json", username=username, json=parameters)
        return self.construct_post_response(post)

    @Registry.action(
        slug="delete-post",
        description="Delete a post",
        input_schema=Schemas.delete_post_or_topic_parameters,
        output_schema=None,
    )
    def delete_post(self, parameters):
        self.discourse_request("DELETE", f"posts/{parameters['id']}")
        return {}

    @Registry.action(
        slug="delete-topic",
        description="Delete a topic",
        input_schema=Schemas.delete_post_or_topic_parameters,
        output_schema=None,
    )
    def delete_topic(self, parameters):
        self.discourse_request("DELETE", f"t/{parameters['id']}.json")
        return {}

    @Registry.action(
        slug="recover-post",
        description="Recover a deleted post",
        input_schema=Schemas.delete_post_or_topic_parameters,
        output_schema=None,
    )
    def recover_post(self, parameters):
        self.discourse_request("PUT", f"posts/{parameters['id']}/recover")
        return {}

    @Registry.action(
        slug="recover-topic",
        description="Recover a deleted topic",
        input_schema=Schemas.delete_post_or_topic_parameters,
        output_schema=None,
    )
    def recover_topic(self, parameters):
        self.discourse_request("PUT", f"t/{parameters['id']}/recover")
        return {}

    @Registry.action(
        slug="lock-post",
        description="Lock or unlock a post on discourse",
        input_schema=Schemas.lock_post_parameters,
        output_schema=Schemas.lock_post_response,
    )
    def lock_post(self, parameters):
        post_id = parameters["id"]
        data = {"locked": json.dumps(parameters["locked"])}
        return self.discourse_request("PUT", f"posts/{post_id}/locked", data=data)

    def validate_request_signature(self, request):
        event_signature = request.headers.get("X-Discourse-Event-Signature")
        if not event_signature:
            raise PluginErrorInternal("Missing event signature")
        key = bytes(self.config["webhook_secret"], "utf-8")
        string_signature = hmac.new(key, request.body, hashlib.sha256).hexdigest()
        expected_signature = f"sha256={string_signature}"
        if not hmac.compare_digest(event_signature, expected_signature):
            raise PluginErrorInternal("Invalid signature header")

        instance = request.headers["X-Discourse-Instance"]
        if instance != self.config["server_url"]:
            raise PluginErrorInternal("Unexpected X-Discourse-Instance")

    def receive_webhook(self, request):
        self.validate_request_signature(request)
        event = request.headers.get("X-Discourse-Event")
        body = json.loads(request.body)
        logger.info(f"Received event '{event}' from Discourse")

        if event == "post_created":
            post = body.get("post")
            data = {
                "raw": post["raw"],
                "topic_id": post["topic_id"],
                "id": post["id"],
                "url": self.construct_post_url(post),
            }
            initiator = {"user_id": post["username"], "provider": "discourse"}
            self.send_event_to_driver(event_type=EVENT_POST_CREATED, initiator=initiator, data=data)
        elif event == "topic_created":
            topic = body.get("topic")
            data = {
                "title": topic["title"],
                "id": topic["id"],
                "tags": topic["tags"],
                "category": topic["category_id"],
                "url": self.construct_topic_url(topic),
            }
            initiator = {"user_id": topic["created_by"]["username"], "provider": "discourse"}
            self.send_event_to_driver(event_type=EVENT_TOPIC_CREATED, initiator=initiator, data=data)


"""
GOVERNANCE PROCESSES
"""


@Registry.governance_process
class DiscoursePoll(GovernanceProcess):
    name = "poll"
    plugin_name = "discourse"

    input_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "options": {"type": "array", "items": {"type": "string"}},
            "details": {"type": "string"},
            "category": {"type": "integer"},
            "closing_at": {"type": "string", "format": "date"},
        },
        "required": ["title", "options"],
    }
    # TODO: define outcome schema

    class Meta:
        proxy = True

    def start(self, parameters) -> None:
        discourse_server_url = self.plugin.config["server_url"]
        url = f"{discourse_server_url}/posts.json"

        closes_at = ""
        if parameters.get("closing_at"):
            closes_at = "close=" + parameters["closing_at"]
        options = "".join([f"* {opt}\n" for opt in parameters["options"]])
        raw = f"""
{parameters.get("details") or ""}
[poll type=regular results=always chartType=bar {closes_at}]
# {parameters["title"]}
{options}
[/poll]
        """
        payload = {"raw": raw, "title": parameters["title"]}
        if parameters.get("category"):
            payload["category"] = parameters["category"]
        headers = {"Api-Key": self.plugin.config["api_key"], "Api-Username": "system"}
        logger.info(payload)
        logger.info(url)

        resp = requests.post(url, data=payload, headers=headers)
        if not resp.ok:
            logger.error(f"Error: {resp.status_code} {resp.text}")
            raise PluginErrorInternal(resp.text or "unknown error")

        response = resp.json()
        if response.get("errors"):
            errors = response["errors"]
            raise PluginErrorInternal(str(errors))

        poll_url = f"{discourse_server_url}/t/{response.get('topic_slug')}/{response.get('topic_id')}"
        logger.info(f"Poll created at {poll_url}")
        self.state.set("post_id", response.get("id"))
        self.state.set("topic_id", response.get("topic_id"))
        self.state.set("topic_slug", response.get("topic_slug"))

        self.outcome = {"poll_url": poll_url}  # this gets serialized and returned
        self.status = ProcessStatus.PENDING.value
        self.save()

    def update(self):
        """
        We make a request to Discourse EVERY time, here, so that we can catch cases where the poll was closed
        manually by a user. Would be simplified if we disallow that, and instead this function could just
        check if `closing_at` has happened yet (if set) and call close() if it has.
        """
        headers = {"Api-Username": "system", "Api-Key": self.plugin.config["api_key"]}
        topic_id = self.state.get("topic_id")
        resp = requests.get(f"{self.plugin.config['server_url']}/t/{topic_id}.json", headers=headers)
        if not resp.ok:
            logger.error(f"{resp.status_code} {resp.reason}")
            raise PluginErrorInternal(resp.text)
        response = resp.json()
        topic_post = response["post_stream"]["posts"][0]
        poll = topic_post["polls"][0]
        self.update_outcome_from_discourse_poll(poll)

    def close(self):
        """
        Invoked by the Driver to manually close the poll. This would be used in cases where `closing_at` param is not set,
        or in cases where the Driver wants to close the poll early (before closing_at time).
        """
        url = f"{self.plugin.config['server_url']}/polls/toggle_status"
        post_id = self.state.get("post_id")
        data = {"post_id": post_id, "poll_name": "poll", "status": "closed"}
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Api-Username": "system",
            "Api-Key": self.plugin.config["api_key"],
        }

        resp = requests.put(url, data=data, headers=headers)
        if not resp.ok:
            logger.error(f"{resp.status_code} {resp.reason} {resp.text}")
            raise PluginErrorInternal(resp.text)
        poll = resp.json()["poll"]
        self.update_outcome_from_discourse_poll(poll)

        # Lock the post
        # self.get_plugin().lock_post({"locked": True, "id": post_id})

    def update_outcome_from_discourse_poll(self, poll):
        """Save changes to outcome and state if changed"""
        dirty = False
        votes = self.outcome.get("votes", {})
        for opt in poll["options"]:
            key = opt["html"]
            val = opt["votes"]
            if votes.get(key) != val:
                votes[key] = val
                dirty = True

        if poll["status"] == "closed":
            self.status = ProcessStatus.COMPLETED.value
            dirty = True

        if dirty:
            logger.info(f"{self}: {self.outcome}")
            self.outcome["votes"] = votes
            self.save()
