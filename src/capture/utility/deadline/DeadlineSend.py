import socket

import http.client

import json

import urllib.request, urllib.error, urllib.parse

import traceback



def send(address, message, requestType, useAuth=False, username="", password=""):

    """

        Used for sending requests that do not require message body, like GET and DELETE.

        Params: address of the webservice (string).

                message to the webservice (string).

                request type for the message (string, GET or DELETE).

    """

    try:

        if not address.startswith("http://"):

            address = "http://"+address

        url = address + message

        

        if useAuth:

            password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()



            password_mgr.add_password(None, url, username, password)



            handler = urllib.request.HTTPBasicAuthHandler(password_mgr)

            opener = urllib.request.build_opener(handler)

            request = urllib.request.Request(url)

            request.get_method = lambda: requestType

            

            response = opener.open(request)

        else:

            opener = urllib.request.build_opener(urllib.request.HTTPHandler)

            request = urllib.request.Request(url)

            request.get_method = lambda: requestType

            

            response = opener.open(request)



        data = response.read()

            

        data = data.replace(b'\n',b' ')

        

    except urllib.error.HTTPError as err:

        data = traceback.format_exc()

        if err.code == 401:

            data = "Error: HTTP Status Code 401. Authentication with the Web Service failed. Please ensure that the authentication credentials are set, are correct, and that authentication mode is enabled."

        else:

            data = err.read()

    try:

        data = json.loads(data)

    except:

        pass



    return data

    

def pSend(address, message, requestType, body, useAuth=False, username="", password=""):

    """

        Used for sending requests that require a message body, like PUT and POST.

        Params: address of the webservice (string).

                message to the webservice (string).

                request type for the message (string, PUT or POST).

                message body for the request (string, JSON object).

    """

    response = ""

    try:

        if not address.startswith("http://"):

            address = "http://"+address

        url = address + message

        

        if useAuth:

            password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()

            

            password_mgr.add_password(None, url, username, password)



            handler = urllib.request.HTTPBasicAuthHandler(password_mgr)

            opener = urllib.request.build_opener(handler)

            

            request = urllib.request.Request(url, data=body)

            request.get_method = lambda: requestType

            

            response = opener.open(request)

        

        else:

            opener = urllib.request.build_opener(urllib.request.HTTPHandler)

            request = urllib.request.Request(url, data=body.encode())

            request.get_method = lambda: requestType

            response = opener.open(request)

            

        data = response.read()



    except urllib.error.HTTPError as err:

        data = traceback.format_exc()

        if err.code == 401:

            data = "Error: HTTP Status Code 401. Authentication with the Web Service failed. Please ensure that the authentication credentials are set, are correct, and that authentication mode is enabled."

        else:

            data = err.read()



        

    try:

        data = json.loads(data)

    except:

        pass

        

    return data