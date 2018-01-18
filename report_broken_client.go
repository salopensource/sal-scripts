package main

import (
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"strings"

	"github.com/groob/mackit/cfpref"
)

func getSerialNumber() (string, error) {
	out, err := exec.Command("/usr/sbin/ioreg", "-l").Output()
	if err != nil {
		log.Fatal(err)
	}
	for _, l := range strings.Split(string(out), "\n") {
		if strings.Contains(l, "IOPlatformSerialNumber") {
			s := strings.Split(l, " ")
			t := strings.Replace(s[len(s)-1], "\"", "", -1)
			return t, nil
		}
	}
	return "", errors.New("could not retrieve serial number")
}

func main() {
	serialNumber, err := getSerialNumber()
	if err != nil {
		log.Fatalf("Could not retrieve serial number")
	}
	salUrl := cfpref.CopyAppValue("ServerURL", "com.github.salopensource.sal")
	key := cfpref.CopyAppValue("key", "com.github.salopensource.sal")

	//Testing
	// salUrl := "http://127.0.0.1:8000"
	// Now you all know the key for my test group on my computer.
	// key := "2k4wohv0sopmzkfp5ocubal47iwds8ddz8h4w7kjbcdjmbyhlgiztdyj7e8up048l89u35vqt08l4jrrkmaegj0j9ba264g3r80geybog0e9e2wrik6jqow7wh4fb5az"

	theUrl, err := url.Parse(fmt.Sprintf("%v", salUrl))
	if err != nil {
		log.Fatal(err)
	}
	theUrl.Path = "/checkin/"
	theKey := fmt.Sprintf("%v", key)

	v := url.Values{}
	v.Set("broken_client", "True")
	v.Set("key", theKey)
	v.Set("serial", serialNumber)

	req, err := http.NewRequest("POST", theUrl.String(), strings.NewReader(v.Encode()))
	if err != nil {
		log.Fatalf("failed to create request: %s", err)
	}

	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	req.SetBasicAuth("sal", theKey)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		log.Fatalf("failed to checkin: %s", err)
	}

	defer resp.Body.Close()

	io.Copy(os.Stdout, resp.Body)
}
