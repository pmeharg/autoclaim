#!/usr/bin/env python

from pprint import pprint
import json
from time import sleep
import requests
import os
from datetime import datetime

# get unknown hashes from report - creates array of hashes
# check hashes in repo
# get metadata for hashes - add to array of hashes
# go back into report claim for each hash using metadata


# Environment variables
iq_url = "http://localhost:8070"
username = "admin"
password = "admin1234"
user_input_app_name = "prop-comp-claim"
user_input_stage = "build"
repository_ID = "maven-releases"

theurl = iq_url + "/api/v2/applications/"


def get_json_report():

    r = requests.get(theurl, auth=(username, password))

    json_data = json.loads(r.text)

    for applications in json_data['applications']:
        app_name = str(applications['name'])
        app_id = str(applications['publicId'])
        app_id_hash = str(applications['id'])

        if app_name == user_input_app_name:
            theurl2 = iq_url + "/api/v2/reports/applications/" + str(app_id_hash)
            res2 = requests.get(theurl2, auth=(username, password))
            json_data_reps = json.loads(res2.text)

            # gets url for build stage of app / BOM
            for items in json_data_reps:
                stage = items['stage']
                reporturl = items['reportDataUrl']
                if stage == user_input_stage:
                    theurl3 = iq_url + '/' + str(reporturl)
                    res3 = requests.get(theurl3, auth=(username, password))
                    json_data_comps = json.loads(res3.text)
    return json_data_comps


def get_hash_from_report_and_claim(json_data_comps):
    for component in json_data_comps['components']:
        if (component['matchState'] == 'unknown'):
            hash_id = [component['hash'], component['pathnames']]
            full_hash = search_repo_using_hash(hash_id)
            # sleep(2)
            # pprint(full_hash)
            claim_component_in_IQ_report(full_hash)
        else:
            print("The component is known...doing nothing")


def search_repo_using_hash(hash):
    search_endpoint = 'http://localhost:8072/service/rest/v1/search'
    #print(search_endpoint)

    headers = {'Accept':'application/json'}
    params = (
        ('q', str(hash[0]) + '*'),
        ('repository', repository_ID),
    )
    r = requests.get(search_endpoint, headers=headers, params=params)
    repo_component = json.loads(r.text)

    pprint(repo_component)

    if repo_component['items'] != []:
        sleep(3)
        # pprint(repo_component)
        group = str(repo_component['items'][0]['group'])
        group = group.replace('/', '-')
        print(group[:1] + "this is the first char of group")
        if group[:1] == '-':
            group = group[1:]
        print("The group ID is: " +  str(group))
        artifact = str(repo_component['items'][0]['name'])
        artifact = artifact.replace('/', '-')
        print("The artifact ID is: " + str(artifact))
        extension = artifact[-4:]
        if extension[:1] == ".":
            extension = extension[-3:]
        print(str(extension) + " This is the extension")
        version = repo_component['items'][0]['version']
        print(version)
        # pprint(repo_component['items'][0]['assets'][0]['downloadUrl'])

        hash.append(group)
        hash.append(artifact)
        hash.append(version)
        hash.append(extension)

    return (hash)


def claim_component_in_IQ_report(unknown_component):
    if len(unknown_component) > 2:
        hash = unknown_component[0]
        group = unknown_component[2]
        artifact = unknown_component[3]
        version = unknown_component[4]
        # date = str(datetime.now())
        extension = unknown_component[5]

        # pprint(unknown_component)

        headers = {"Content-Type": "application/json;charset=UTF-8"}
        data = {

            "hash": hash,
            "comment": "",
            "createTime": 1444172400000,
            "componentIdentifier": {
                "format": "maven",
                "coordinates": {
                    "groupId": group,
                    "artifactId": artifact,
                    "version": version,
                    "classifier": "",
                    "extension": extension
                }
            }
        }

        pprint(data)
        
        iq_session = requests.Session()
        iq_session.auth = requests.auth.HTTPBasicAuth(username, password)
        iq_session.cookies.set('CLM-CSRF-TOKEN', 'api')
        iq_headers = {'X-CSRF-TOKEN': 'api'}

        r = iq_session.post("{}/rest/component/identified".format(iq_url), json=data, headers=iq_headers)

        print(r.status_code)

        # print r.status_code
        if str(r.status_code) == "200":
            print("Your components were successfuly autoclaimed in the IQ server")
        else:
            print("Error, unsucessful autoclaim of the components in the IQ server - contact support")
            print(r)


if __name__ == "__main__":
    json_report = get_json_report()
    get_hash_from_report_and_claim(json_report)
