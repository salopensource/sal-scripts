#!/usr/bin/python
from salgurl import SalGurl
import tempfile
from Foundation import *
import os
import sys
BUNDLE_ID = 'com.github.salopensource.sal'
class GurlError(Exception):
    pass

class HTTPError(Exception):
    pass

def set_pref(pref_name, pref_value):
    """Sets a preference, writing it to
        /Library/Preferences/com.salopensource.sal.plist.
        This should normally be used only for 'bookkeeping' values;
        values that control the behavior of munki may be overridden
        elsewhere (by MCX, for example)"""
    try:
        CFPreferencesSetValue(
                              pref_name, pref_value, BUNDLE_ID,
                              kCFPreferencesAnyUser, kCFPreferencesCurrentHost)
        CFPreferencesAppSynchronize(BUNDLE_ID)
    except Exception:
        pass

def pref(pref_name):
    """Return a preference. Since this uses CFPreferencesCopyAppValue,
    Preferences can be defined several places. Precedence is:
        - MCX
        - /var/root/Library/Preferences/com.salopensource.sal.plist
        - /Library/Preferences/com.salopensource.sal.plist
        - default_prefs defined here.
    """
    default_prefs = {
        'ServerURL': 'http://sal',
        'osquery_launchd': 'com.facebook.osqueryd.plist'
    }
    pref_value = CFPreferencesCopyAppValue(pref_name, BUNDLE_ID)
    if pref_value == None:
        pref_value = default_prefs.get(pref_name)
        # we're using a default value. We'll write it out to
        # /Library/Preferences/<BUNDLE_ID>.plist for admin
        # discoverability
        set_pref(pref_name, pref_value)
    if isinstance(pref_value, NSDate):
        # convert NSDate/CFDates to strings
        pref_value = str(pref_value)
    return pref_value

def post_url(url, post_data, destinationpath, debug=False, message=None, follow_redirects=True,
            progress_method=None):
    """Sends POST data to a URL and then returns the result.
    Accepts the URL to send the POST to, URL encoded data and
    optionally can follow redirects
    """
    tempdownloadpath = destinationpath + '.download'
    if os.path.exists(tempdownloadpath):
        os.remove(tempdownloadpath)
    options = {'url': url,
               'file': tempdownloadpath,
               'follow_redirects': follow_redirects,
               'post_data': post_data,
               'connection_timeout': 60,
               'logging_function': NSLog}
    # NSLog('gurl options: %@', options)
    if debug:
        NSLog('url: %@', options['url'])
    connection = SalGurl.alloc().initWithOptions_(options)
    stored_percent_complete = -1
    stored_bytes_received = 0
    connection.start()
    try:
        while True:
            # if we did `while not connection.isDone()` we'd miss printing
            # messages and displaying percentages if we exit the loop first
            connection_done = connection.isDone()
            if message and connection.status and connection.status != 304:
                # log always, display if verbose is 1 or more
                # also display in progress field
                if debug:
                    NSLog(message)
                if progress_method:
                    progress_method(None, None, message)
                # now clear message so we don't display it again
                message = None
            if (str(connection.status).startswith('2')
                    and connection.percentComplete != -1):
                if connection.percentComplete != stored_percent_complete:
                    # display percent done if it has changed
                    stored_percent_complete = connection.percentComplete
                    if debug:
                        NSLog('Percent done: %@', stored_percent_complete)
                    if progress_method:
                        progress_method(None, stored_percent_complete, None)
            elif connection.bytesReceived != stored_bytes_received:
                # if we don't have percent done info, log bytes received
                stored_bytes_received = connection.bytesReceived
                if debug:
                    NSLog('Bytes received: %@', stored_bytes_received)
                if progress_method:
                    progress_method(None, None,
                                    'Bytes received: %s'
                                    % stored_bytes_received)
            if connection_done:
                break

    except (KeyboardInterrupt, SystemExit):
        # safely kill the connection then re-raise
        connection.cancel()
        raise
    except Exception, err: # too general, I know
        # Let us out! ... Safely! Unexpectedly quit dialogs are annoying...
        connection.cancel()
        # Re-raise the error as a GurlError
        # if len(err) != 0:
        #     raise GurlError(-1, str(err))

    if connection.error != None:
        # Gurl returned an error
        if debug:
            NSLog('Download error %@: %@', connection.error.code(),
              connection.error.localizedDescription())
        if connection.SSLerror:
            NSLog('SSL error detail: %@', str(connection.SSLerror))
        if debug:
            NSLog('Headers: %@', str(connection.headers))
        raise GurlError(connection.error.code(),
                        connection.error.localizedDescription())

    if connection.response != None:
        if debug:
            NSLog('Status: %@', connection.status)
            NSLog('Headers: %@', connection.headers)
    if connection.redirection != []:
        if debug:
            NSLog('Redirection: %@', connection.redirection)

    connection.headers['http_result_code'] = str(connection.status)
    description = NSHTTPURLResponse.localizedStringForStatusCode_(
        connection.status)
    connection.headers['http_result_description'] = description

    # try:
    #     os.unlink(temp_file)
    #     os.rmdir(os.path.dirname(temp_file))
    # except (OSError, IOError):
    #     pass
    temp_download_exists = os.path.isfile(tempdownloadpath)
    connection.headers['http_result_code'] = str(connection.status)
    description = NSHTTPURLResponse.localizedStringForStatusCode_(
        connection.status)
    connection.headers['http_result_description'] = description

    if str(connection.status).startswith('2') and temp_download_exists:
        os.rename(tempdownloadpath, destinationpath)
        return connection.headers
    elif connection.status == 304:
        # unchanged on server
        if debug:
            NSLog('Item is unchanged on the server.')
        return connection.headers
    else:
        # there was an HTTP error of some sort
        raise HTTPError(connection.status,
                        connection.headers.get('http_result_description', ''))

def get_url(url, destinationpath, debug=False, message=None, follow_redirects=True,
            progress_method=None):
    """Gets an HTTP or HTTPS URL and stores it in
    destination path. Returns a dictionary of headers, which includes
    http_result_code and http_result_description.
    Will raise GurlError if Gurl returns an error.
    Will raise HTTPError if HTTP Result code is not 2xx or 304.
    If destinationpath already exists, you can set 'onlyifnewer' to true to
    indicate you only want to download the file only if it's newer on the
    server.
    If you set resume to True, Gurl will attempt to resume an
    interrupted download."""

    tempdownloadpath = destinationpath + '.download'
    if os.path.exists(tempdownloadpath):
        os.remove(tempdownloadpath)

    options = {'url': url,
               'file': tempdownloadpath,
               'follow_redirects': follow_redirects,
               'logging_function': NSLog}
   # NSLog('gurl options: %@', options)

    connection = SalGurl.alloc().initWithOptions_(options)
    stored_percent_complete = -1
    stored_bytes_received = 0
    connection.start()
    try:
        while True:
            # if we did `while not connection.isDone()` we'd miss printing
            # messages and displaying percentages if we exit the loop first
            connection_done = connection.isDone()
            if message and connection.status and connection.status != 304:
                # log always, display if verbose is 1 or more
                # also display in progress field
                if debug:
                    NSLog(message)
                if progress_method:
                    progress_method(None, None, message)
                # now clear message so we don't display it again
                message = None
            if (str(connection.status).startswith('2')
                    and connection.percentComplete != -1):
                if connection.percentComplete != stored_percent_complete:
                    # display percent done if it has changed
                    stored_percent_complete = connection.percentComplete
                    if debug:
                        NSLog('Percent done: %@', stored_percent_complete)
                    if progress_method:
                        progress_method(None, stored_percent_complete, None)
            elif connection.bytesReceived != stored_bytes_received:
                # if we don't have percent done info, log bytes received
                stored_bytes_received = connection.bytesReceived
                if debug:
                    NSLog('Bytes received: %@', stored_bytes_received)
                if progress_method:
                    progress_method(None, None,
                                    'Bytes received: %s'
                                    % stored_bytes_received)
            if connection_done:
                break

    except (KeyboardInterrupt, SystemExit):
        # safely kill the connection then re-raise
        connection.cancel()
        raise
    except Exception, err: # too general, I know
        # Let us out! ... Safely! Unexpectedly quit dialogs are annoying...
        connection.cancel()
        # Re-raise the error as a GurlError
        raise GurlError(-1, str(err))

    if connection.error != None:
        # Gurl returned an error
        if debug:
            NSLog('Download error %@: %@', connection.error.code(),
              connection.error.localizedDescription())
        if connection.SSLerror:
            NSLog('SSL error detail: %@', str(connection.SSLerror))
        if debug:
            NSLog('Headers: %@', str(connection.headers))
        if os.path.exists(tempdownloadpath):
            os.remove(tempdownloadpath)
        raise GurlError(connection.error.code(),
                        connection.error.localizedDescription())

    if connection.response != None:
        if debug:
            NSLog('Status: %@', connection.status)
            NSLog('Headers: %@', connection.headers)
    if connection.redirection != []:
        if debug:
            NSLog('Redirection: %@', connection.redirection)

    temp_download_exists = os.path.isfile(tempdownloadpath)
    connection.headers['http_result_code'] = str(connection.status)
    description = NSHTTPURLResponse.localizedStringForStatusCode_(
        connection.status)
    connection.headers['http_result_description'] = description

    if str(connection.status).startswith('2') and temp_download_exists:
        os.rename(tempdownloadpath, destinationpath)
        return connection.headers
    elif connection.status == 304:
        # unchanged on server
        if debug:
            NSLog('Item is unchanged on the server.')
        return connection.headers
    else:
        # there was an HTTP error of some sort; remove our temp download.
        if os.path.exists(tempdownloadpath):
            try:
                os.unlink(tempdownloadpath)
            except OSError:
                pass
        raise HTTPError(connection.status,
                        connection.headers.get('http_result_description', ''))