package main

import (
	"fmt"
	"io/ioutil"
	"net/http"
	"net/url"
	"os/exec"
	"strings"

	"github.com/groob/mackit/cfpref"
)

func serialNumber() string {
	out, err := exec.Command("/usr/sbin/ioreg", "-l").Output()
	if err != nil {
		return ""
	}
	for _, l := range strings.Split(string(out), "\n") {
		if strings.Contains(l, "IOPlatformSerialNumber") {
			s := strings.Split(l, " ")
			t := strings.Replace(s[len(s)-1], "\"", "", -1)
			return t
		}
	}
	return ""
}

func main() {
	serial_number := serialNumber()
	if serial_number == "" {
		panic("Could not retrieve serial number")
	}
	sal_url := cfpref.CopyAppValue("ServerURL", "com.github.salopensource.sal")
	key := cfpref.CopyAppValue("key", "com.github.salopensource.sal")

	//Testing
	// sal_url := "http://127.0.0.1:8000"
	// Now you all know the key for my test group on my computer.
	// key := "2k4wohv0sopmzkfp5ocubal47iwds8ddz8h4w7kjbcdjmbyhlgiztdyj7e8up048l89u35vqt08l4jrrkmaegj0j9ba264g3r80geybog0e9e2wrik6jqow7wh4fb5az"

	the_url := fmt.Sprintf("%v/checkin/", sal_url)
	the_key := fmt.Sprintf("%v", key)

	v := url.Values{}
	v.Set("broken_client", "True")
	v.Set("key", the_key)
	v.Set("serial", serial_number)

	req, err := http.NewRequest("POST", the_url, strings.NewReader(v.Encode()))
	if err != nil {
		panic(fmt.Errorf("failed to create request: %s", err))
	}

	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	req.SetBasicAuth("sal", the_key)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		panic(fmt.Errorf("failed to checkin: %s", err))
	}

	defer resp.Body.Close()

	bodyBytes, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		panic(err)
	}

	bodyString := string(bodyBytes)

	fmt.Println(bodyString)
}
