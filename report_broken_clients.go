package main

import (
    "fmt"
    // "log"
    // "io/ioutil"
    // "time"
    // "os"
    "os/exec"
    "strings"

    "github.com/groob/mackit/cfpref"
    // "gopkg.in/yaml.v2"
    // "github.com/groob/plist"
)

func SerialNumber() string {
    out, _ := exec.Command("/usr/sbin/ioreg", "-l").Output() // err ignored for brevity
    for _, l := range strings.Split(string(out), "\n") {
        if strings.Contains(l, "IOPlatformSerialNumber") {
            s := strings.Split(l, " ")
            t := strings.Replace(s[len(s)-1], "\"", "", -1)
            return t
        }
    }
    return ""
}

// func GetPref(preference string, key string) string {
//     theKey := fmt.Sprintf("$.CFPreferencesCopyAppValue('%s',", key)
//     thePreference := fmt.Sprintf("'%s');", preference)

//     out, err := exec.Command("osascript", "-l", "JavaScript", "-e,", "\"ObjC.import('Foundation');", theKey, thePreference).Output()
//     fmt.Printf("%s", string(out[:]))
//     if err != nil {
        
//         log.Fatal(err)
//     }

//     return string(out[:])
// }

func main() {
    //fmt.Printf("%s", SerialNumber())
    url := cfpref.CopyAppValue("ServerURL", "com.github.salopensource.sal")
    key := cfpref.CopyAppValue("key", "com.github.salopensource.sal")
    fmt.Println(url)
    fmt.Println(key)
}
