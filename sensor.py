"""GitHub sensor platform."""
from datetime import timedelta
import logging
import re
from typing import Any, Callable, Dict, Optional

from homeassistant import config_entries, core
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_NAME,
    CONF_ACCESS_TOKEN,
    CONF_NAME,
    CONF_PATH,
    CONF_URL,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)

import voluptuous as vol

from .const import DOMAIN, LISTENING_PORT
from .server import LoggerServer

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([LoggerServerEntity(config, async_add_entities)])


class LoggerServerEntity(Entity):
    should_poll = False
    unique_id = 'solis_ginglong_local_logger_server'
    name = 'Solis/Ginglong Local Logger Server'

    def __init__(self, config_data, async_add_entities):
        _LOGGER.error("Config data: %s", config_data)
        self._server = LoggerServer(config_data[LISTENING_PORT], self._on_data)
        self._async_add_entities = async_add_entities
        self._inverters = dict()

    def _on_data(self, data: Dict[str, Any]):
        _LOGGER.error("Got data: %s", data)
        inverter_id = data["inverter_serial_number"]
        inverter_logger = self._inverters.get(inverter_id, None)
        if inverter_logger is None:
            _LOGGER.error("Creating new inverter logger for %s", inverter_id)
            inverter_logger = InverterLogEntity(inverter_id)
            self._inverters[inverter_id] = inverter_logger
            self._async_add_entities([inverter_logger])
        inverter_logger.set_data(data)

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        await self._server.start_server()

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        await self._server.stop_server()


class InverterLogEntity(Entity):
    should_poll = False

    def __init__(self, inverter_id):
        self._inverter_id = inverter_id

    def set_data(self, data):
        self._data = data

    @property
    def name(self) -> str:
        return f"{self._inverter_id} Logger"

    @property
    def state(self) -> float:
        return self._data["inverter_temperature"]

    @property
    def unique_id(self) -> str:
        return self._inverter_id

# class GitHubRepoSensor(Entity):
#     """Representation of a GitHub Repo sensor."""

#     def __init__(self, github: GitHubAPI, repo: Dict[str, str]):
#         super().__init__()
#         self.github = github
#         self.repo = repo["path"]
#         self.attrs: Dict[str, Any] = {ATTR_PATH: self.repo}
#         self._name = repo.get("name", self.repo)
#         self._state = None
#         self._available = True

#     @property
#     def name(self) -> str:
#         """Return the name of the entity."""
#         return self._name

#     @property
#     def unique_id(self) -> str:
#         """Return the unique ID of the sensor."""
#         return self.repo

#     @property
#     def available(self) -> bool:
#         """Return True if entity is available."""
#         return self._available

#     @property
#     def state(self) -> Optional[str]:
#         return self._state

#     @property
#     def device_state_attributes(self) -> Dict[str, Any]:
#         return self.attrs

#     async def async_update(self):
#         try:
#             repo_url = f"/repos/{self.repo}"
#             repo_data = await self.github.getitem(repo_url)
#             self.attrs[ATTR_FORKS] = repo_data["forks_count"]
#             self.attrs[ATTR_NAME] = repo_data["name"]
#             self.attrs[ATTR_STARGAZERS] = repo_data["stargazers_count"]

#             if repo_data["permissions"]["push"]:
#                 clones_url = f"{repo_url}/traffic/clones"
#                 clones_data = await self.github.getitem(clones_url)
#                 self.attrs[ATTR_CLONES] = clones_data["count"]
#                 self.attrs[ATTR_CLONES_UNIQUE] = clones_data["uniques"]

#                 views_url = f"{repo_url}/traffic/views"
#                 views_data = await self.github.getitem(views_url)
#                 self.attrs[ATTR_VIEWS] = views_data["count"]
#                 self.attrs[ATTR_VIEWS_UNIQUE] = views_data["uniques"]

#             commits_url = f"/repos/{self.repo}/commits"
#             commits_data = await self.github.getitem(commits_url)
#             latest_commit = commits_data[0]
#             self.attrs[ATTR_LATEST_COMMIT_MESSAGE] = latest_commit["commit"]["message"]
#             self.attrs[ATTR_LATEST_COMMIT_SHA] = latest_commit["sha"]

#             # Using the search api to fetch open PRs.
#             prs_url = f"/search/issues?q=repo:{self.repo}+state:open+is:pr"
#             prs_data = await self.github.getitem(prs_url)
#             self.attrs[ATTR_OPEN_PULL_REQUESTS] = prs_data["total_count"]
#             if prs_data and prs_data["items"]:
#                 self.attrs[ATTR_LATEST_OPEN_PULL_REQUEST_URL] = prs_data["items"][0][
#                     "html_url"
#                 ]

#             issues_url = f"/repos/{self.repo}/issues"
#             issues_data = await self.github.getitem(issues_url)
#             # GitHub issues include pull requests, so to just get the number of issues,
#             # we need to subtract the total number of pull requests from this total.
#             total_issues = repo_data["open_issues_count"]
#             self.attrs[ATTR_OPEN_ISSUES] = (
#                 total_issues - self.attrs[ATTR_OPEN_PULL_REQUESTS]
#             )
#             if issues_data:
#                 self.attrs[ATTR_LATEST_OPEN_ISSUE_URL] = issues_data[0]["html_url"]

#             releases_url = f"/repos/{self.repo}/releases"
#             releases_data = await self.github.getitem(releases_url)
#             if releases_data:
#                 self.attrs[ATTR_LATEST_RELEASE_URL] = releases_data[0]["html_url"]
#                 self.attrs[ATTR_LATEST_RELEASE_TAG] = releases_data[0][
#                     "html_url"
#                 ].split("/")[-1]

#             # Set state to short commit sha.
#             self._state = latest_commit["sha"][:7]
#             self._available = True
#         except (ClientError, gidgethub.GitHubException):
#             self._available = False
#             _LOGGER.exception(
#                 "Error retrieving data from GitHub for sensor %s.", self.name
#             )
