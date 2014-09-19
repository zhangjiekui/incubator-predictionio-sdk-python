"""PredictoinIO Python SDK

The PredictoinIO Python SDK provides easy-to-use functions for integrating
Python applications with PredictionIO REST API services.
"""

__author__ = "The PredictionIO Team"
__email__ = "help@tappingstone.com"
__copyright__ = "Copyright 2014, TappingStone, Inc."
__license__ = "Apache License, Version 2.0"

__version__ = "0.8.0-SNAPSHOT"

# import deprecated libraries.
from predictionio.obsolete import Client

# import packages
import re
try:
  import httplib
except ImportError:
  # pylint: disable=F0401
  # http is a Python3 module, replacing httplib
  from http import client as httplib
import json
import urllib

from predictionio.connection import Connection
from predictionio.connection import AsyncRequest
from predictionio.connection import PredictionIOAPIError

class NotCreatedError(PredictionIOAPIError):
  pass

class NotFoundError(PredictionIOAPIError):
  pass

class BaseClient(object):
  def __init__(self, url, threads=1, qsize=0, timeout=5):
    """Constructor of Client object.

    """
    self.threads = threads
    self.url = url
    self.qsize = qsize
    self.timeout = timeout

    # check connection type
    https_pattern = r'^https://(.*)'
    http_pattern = r'^http://(.*)'
    m = re.match(https_pattern, url)
    self.https = True
    if m is None:  # not matching https
      m = re.match(http_pattern, url)
      self.https = False
      if m is None:  # not matching http either
        raise InvalidArgumentError("url is not valid: %s" % url)
    self.host = m.group(1)

    self._uid = None  # identified uid
    self._connection = Connection(host=self.host, threads=self.threads,
                    qsize=self.qsize, https=self.https,
                    timeout=self.timeout)

  def close(self):
    """Close this client and the connection.

    Call this method when you want to completely terminate the connection
    with PredictionIO.
    It will wait for all pending requests to finish.
    """
    self._connection.close()

  def pending_requests(self):
    """Return the number of pending requests.

    :returns:
      The number of pending requests of this client.
    """
    return self._connection.pending_requests()

  def get_status(self):
    """Get the status of the PredictionIO API Server

    :returns:
      status message.

    :raises:
      ServerStatusError.
    """
    path = "/"
    request = AsyncRequest("GET", path)
    request.set_rfunc(self._aget_resp)
    self._connection.make_request(request)
    result = request.get_response()
    return result

  def _acreate_resp(self, response):
    if response.error is not None:
      raise NotCreatedError("Exception happened: %s for request %s" %
                    (response.error, response.request))
    elif response.status != httplib.CREATED:
      raise NotCreatedError("request: %s status: %s body: %s" %
                    (response.request, response.status,
                     response.body))

    return response

  def _aget_resp(self, response):
    if response.error is not None:
      raise NotFoundError("Exception happened: %s for request %s" %
                  (response.error, response.request))
    elif response.status != httplib.OK:
      raise NotFoundError("request: %s status: %s body: %s" %
                  (response.request, response.status,
                   response.body))

    return response.json_body

  def _adelete_resp(self, response):
    if response.error is not None:
      raise NotFoundError("Exception happened: %s for request %s" %
                  (response.error, response.request))
    elif response.status != httplib.OK:
      raise NotFoundError("request: %s status: %s body: %s" %
                  (response.request, response.status,
                   response.body))

    return response.body


class EventClient(BaseClient):
  """Client for importing data into PredictionIO Event Server."""
  def __init__(self, app_id, url="http://localhost:7070",
      threads=1, qsize=0, timeout=5):
    super(EventClient, self).__init__(url, threads, qsize, timeout)
    self.app_id = app_id

  def acreate_event(self, data):
    path = "/events.json"
    request = AsyncRequest("POST", path, **data)
    request.set_rfunc(self._acreate_resp)
    self._connection.make_request(request)
    return request

  def create_event(self, data):
    return self.acreate_event(data).get_response()

  def aget_event(self, event_id):
    enc_event_id = urllib.quote(event_id, "") # replace special char with %xx
    path = "/events/%s.json" % enc_event_id
    request = AsyncRequest("GET", path)
    request.set_rfunc(self._aget_resp)
    self._connection.make_request(request)
    return request

  def get_event(self, event_id):
    return self.aget_event(event_id).get_response()

  def adelete_event(self, event_id):
    enc_event_id = urllib.quote(event_id, "") # replace special char with %xx
    path = "/events/%s.json" % enc_event_id
    request = AsyncRequest("DELETE", path)
    request.set_rfunc(self._adelete_resp)
    self._connection.make_request(request)
    return request

  def delete_event(self, event_id):
    return self.adelete_event(event_id).get_response()

  def aset_user(self, uid, properties={}):
    """set properties of an user"""
    return self.acreate_event({
      "event" : "$set",
      "entityType" : "pio_user",
      "entityId" : uid,
      "properties" : properties,
      "appId" : self.app_id
    })

  def aunset_user(self, uid, properties={}):
    """unset properties of an user"""
    return self.acreate_event({
      "event" : "$unset",
      "entityType" : "pio_user",
      "entityId" : uid,
      "properties" : properties,
      "appId" : self.app_id
    })

  def aset_item(self, iid, properties={}):
    return self.acreate_event({
      "event" : "$set",
      "entityType" : "pio_item",
      "entityId" : iid,
      "properties" : properties,
      "appId" : self.app_id
    })

  def aunset_item(self, iid, properties={}):
    return self.acreate_event({
      "event" : "$unset",
      "entityType" : "pio_item",
      "entityId" : iid,
      "properties" : properties,
      "appId" : self.app_id
    })

  def arecord_user_action_on_item(self, action, uid, iid, properties={}):
    return self.acreate_event({
      "event" : action,
      "entityType" : "pio_user",
      "entityId" : uid,
      "targetEntityType" : "pio_item",
      "targetEntityId": iid,
      "properties" : properties,
      "appId" : self.app_id
    })

  def set_user(self, uid, properties={}):
    return self.aset_user(uid, properties).get_response()

  def set_item(self, iid, properties={}):
    return self.aset_item(iid, properties).get_response()

  def unset_user(self, uid, properties={}):
    return self.aunset_user(uid, properties).get_response()

  def unset_item(self, iid, properties={}):
    return self.aunset_item(iid, properties).get_response()

  def record_user_action_on_item(self, action, uid, iid, properties={}):
    return self.arecord_user_action_on_item(
      action, uid, iid, properties).get_response()


class PredictionClient(BaseClient):
  """Client for extracting prediction results from PredictionIO Engine."""
  def __init__(self, url="http://localhost:8000", threads=1,
      qsize=0, timeout=5):
    super(PredictionClient, self).__init__(url, threads, qsize, timeout)

  def asend_query(self, data):
    path = "/"
    request = AsyncRequest("POST", path, **data)
    request.set_rfunc(self._aget_resp)
    self._connection.make_request(request)
    return request

  def send_query(self, data):
    return self.asend_query(data).get_response()

