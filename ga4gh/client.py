"""
Client classes for the GA4GH reference implementation.
"""
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json
import requests
import posixpath

import ga4gh.protocol as protocol

# suppress warning about using https without cert verification
requests.packages.urllib3.disable_warnings()


class HttpClient(object):
    """
    GA4GH Http Client
    """
    workaroundGoogle = 'google'

    def __init__(self, urlPrefix, debugLevel, workarounds, key):
        self._urlPrefix = urlPrefix
        self._debugLevel = debugLevel
        self._bytesRead = 0
        self._workarounds = workarounds
        self._key = key

    def getBytesRead(self):
        """
        Returns the total number of (non HTTP) bytes read from the server
        by this client.
        """
        return self._bytesRead

    # TODO temporary auth solution
    def _getAuth(self):
        if self._usingWorkaroundsFor(self.workaroundGoogle):
            return {'key': self._key}
        else:
            return {}

    def _usingWorkaroundsFor(self, workaround):
        return workaround in self._workarounds

    def _debugResponse(self, jsonString):
        if self._debugLevel > 1:
            # TODO use a logging output and integrate with HTTP client more
            # nicely... also, logging / error handling in general
            print("json response:")
            pp = json.dumps(
                json.loads(jsonString), sort_keys=True, indent=4)
            print(pp)

    def _checkStatus(self, response):
        if response.status_code != requests.codes.ok:
            print(response.text)
            # TODO use custom exception instead of Exception
            raise Exception("Url {0} had status_code {1}".format(
                response.url, response.status_code))

    def _updateBytesRead(self, jsonString):
        self._bytesRead += len(jsonString)

    def _deserializeResponse(self, response, protocolResponseClass):
        jsonResponseString = response.text
        self._updateBytesRead(jsonResponseString)
        self._debugResponse(jsonResponseString)
        responseObject = protocolResponseClass.fromJsonString(
            jsonResponseString)
        return responseObject

    def _updateNotDone(self, responseObject, protocolRequest):
        if hasattr(responseObject, 'nextPageToken'):
            protocolRequest.pageToken = responseObject.nextPageToken
            notDone = responseObject.nextPageToken is not None
        else:
            notDone = False
        return notDone

    def _doRequest(self, httpMethod, url, protocolResponseClass,
                   httpParams={}, httpData=None):
        """
        Performs a request to the server and returns the response
        """
        headers = {}
        if httpData is not None:
            headers.update({"Content-type": "application/json"})
        params = self._getAuth()
        params.update(httpParams)
        response = requests.request(
            httpMethod, url, params=params, data=httpData, headers=headers)
        self._checkStatus(response)
        return self._deserializeResponse(response, protocolResponseClass)

    def runSearchRequest(self, protocolRequest, objectName,
                         protocolResponseClass, listAttr):
        """
        Runs the specified request at the specified objectName and instantiates
        an object of the specified class. We yield each object in listAttr.
        If pages of results are present, repeat this process until the
        pageToken is null.
        """
        fullUrl = posixpath.join(self._urlPrefix, objectName + '/search')
        notDone = True
        while notDone:
            data = protocolRequest.toJsonString()
            responseObject = self._doRequest(
                'POST', fullUrl, protocolResponseClass, httpData=data)
            for extract in getattr(responseObject, listAttr):
                yield extract
            notDone = self._updateNotDone(responseObject, protocolRequest)

    def runListRequest(self, protocolRequest, url,
                       protocolResponseClass, id_):
        """
        Asks the server to list objects of type protocolResponseClass and
        returns an iterator over the results.
        """
        fullUrl = posixpath.join(self._urlPrefix, url).format(id=id_)
        notDone = True
        while notDone:
            requestDict = protocolRequest.toJsonDict()
            responseObject = self._doRequest(
                'GET', fullUrl, protocolResponseClass, requestDict)
            yield responseObject
            notDone = self._updateNotDone(responseObject, protocolRequest)

    def runGetRequest(self, objectName, protocolResponseClass, id_):
        """
        Requests an object from the server and returns the object of
        type protocolResponseClass that has id id_.
        Used for requests where a single object is the expected response.
        """
        url = "{objectName}/{id}"
        fullUrl = posixpath.join(
            self._urlPrefix, url).format(id=id_, objectName=objectName)
        return self._doRequest('GET', fullUrl, protocolResponseClass)

    def getReferenceSet(self, id_):
        """
        Returns a referenceSet from the server
        """
        return self.runGetRequest(
            "referencesets", protocol.GAReferenceSet, id_)

    def getReference(self, id_):
        """
        Returns a reference from the server
        """
        return self.runGetRequest(
            "references", protocol.GAReference, id_)

    def listReferenceBases(self, protocolRequest, id_):
        """
        Returns an iterator over the bases from the server
        """
        return self.runListRequest(
            protocolRequest, "references/{id}/bases",
            protocol.GAListReferenceBasesResponse, id_)

    def printJsonMessage(self, header, jsonString):
        """
        Prints the specified jsonString to stdout for debugging purposes.
        """
        print("json", header)
        pp = json.dumps(
            json.loads(jsonString), sort_keys=True, indent=4)
        print(pp)

    def searchVariants(self, protocolRequest):
        """
        Returns an iterator over the Variants from the server
        """
        return self.runSearchRequest(
            protocolRequest, "variants",
            protocol.GASearchVariantsResponse, "variants")

    def searchVariantSets(self, protocolRequest):
        """
        Returns an iterator over the VariantSets from the server.
        """
        return self.runSearchRequest(
            protocolRequest, "variantsets",
            protocol.GASearchVariantSetsResponse, "variantSets")

    def searchReferenceSets(self, protocolRequest):
        """
        Returns an iterator over the ReferenceSets from the server.
        """
        return self.runSearchRequest(
            protocolRequest, "referencesets",
            protocol.GASearchReferenceSetsResponse, "referenceSets")

    def searchReferences(self, protocolRequest):
        """
        Returns an iterator over the References from the server
        """
        return self.runSearchRequest(
            protocolRequest, "references",
            protocol.GASearchReferencesResponse, "references")

    def searchCallSets(self, protocolRequest):
        """
        Returns an iterator over the CallSets from the server
        """
        return self.runSearchRequest(
            protocolRequest, "callsets",
            protocol.GASearchCallSetsResponse, "callSets")

    def searchReadGroupSets(self, protocolRequest):
        """
        Returns an iterator over the ReadGroupSets from the server
        """
        return self.runSearchRequest(
            protocolRequest, "readgroupsets",
            protocol.GASearchReadGroupSetsResponse, "readGroupSets")

    def searchReads(self, protocolRequest):
        """
        Returns an iterator over the Reads from the server
        """
        return self.runSearchRequest(
            protocolRequest, "reads",
            protocol.GASearchReadsResponse, "alignments")
