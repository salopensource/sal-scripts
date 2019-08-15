//
//  main.swift
//  report_broken_client
//
//  Created by graham_gilbert on 5/24/18.
//  Copyright © 2018 Sal Opensource. All rights reserved.
//

import Foundation

// This needs to come from prefs

// Get Serial function

func getSerial() -> String {
    let platformExpert = IOServiceGetMatchingService(kIOMasterPortDefault, IOServiceMatching("IOPlatformExpertDevice"))
    let serialNumberAsCFString = IORegistryEntryCreateCFProperty(platformExpert, kIOPlatformSerialNumberKey as CFString, kCFAllocatorDefault, 0)
    return serialNumberAsCFString?.takeUnretainedValue() as! String
}

let defaults = UserDefaults.init(suiteName: "com.github.salopensource.sal")

let key = defaults?.string(forKey: "key") ?? ""

var urlString =  defaults?.string(forKey: "ServerURL") ?? ""

urlString = urlString + "/report_broken_client/"

let serial = getSerial()

// set up the auth

let login = "sal"
let password = key

let userPasswordData = "\(login):\(password)".data(using: .utf8)
let base64EncodedCredential = userPasswordData!.base64EncodedString(options: Data.Base64EncodingOptions.init(rawValue: 0))
let authString = "Basic \(base64EncodedCredential)"

// set up the body

var body = "broken_client=true"
body.append("&serial=\(serial)")
body.append("&key=\(key)")
// set up the URL session

let session = URLSession.init(configuration: URLSessionConfiguration.ephemeral, delegate: nil, delegateQueue: nil)

var dataTask: URLSessionDataTask?
var req = URLRequest.init(url: URL.init(string: urlString)!)

let sema = DispatchSemaphore(value: 0)

let headers = [
    "Accept": "application/text",
    "Content-Type": "application/x-www-form-urlencoded",
    "Authorization" : authString,
]

req.allHTTPHeaderFields = headers

req.httpMethod = "POST"
req.httpBody = body.data(using: .utf8)

dataTask = session.dataTask(with: req) { data, response, error in
    
    if let error = error {
        print(error.localizedDescription)
    } else if let data = data,
        let response = response as? HTTPURLResponse,
        response.statusCode == 200 {
        var responseData:String  = String(data:data, encoding:String.Encoding.utf8)!
        print(responseData)
    } else {
        print("really no beans")
    }
    sema.signal()
}

dataTask?.resume()

sema.wait()
