#!/usr/bin/env python3

import subprocess
import sys
import os
import json
import requests
import sqlite3
import secrets
import hashlib
import time

if __name__ == "__main__":
    #signature_verification code...
    line = " ".join(sys.argv[1:])
    room = os.environ.get('ENO_ROOM')
    bn = line.count('}')
    patt = '}' * bn
    jbx = line.find('{"json')
    jex = line.find(patt,jbx)
    js = line[jbx:jex+bn]
    x = js.replace(" ", ",")
    js = x
    buffer = json.loads(js)
    challenge = buffer['params']['challenge_string']
    id = buffer['params']['controller_id']
    signature = buffer['params']['signature']
    url = "http://127.0.0.1:18089/json_rpc"
    headers = {'content-type': 'application/json'}
    rpc_input2 = {
        "method": "verify",
        "params": {"data": challenge,
        "address":id,
        "signature":signature}
        }
    rpc_input2.update({"jsonrpc": "2.0", "id": "0"})
    response2 = requests.post(url,data=json.dumps(rpc_input2),headers=headers)
    sd = response2.json()
    retval = sd["result"]["good"]
    if retval:
    # Signature is good!
        message_hash = hashlib.sha512( str( js ).encode("utf-8") ).hexdigest()
        dbconnect = sqlite3.connect("/home/user/matrix-eno-bot/eno/scripts/resource_mgr")
        cursor = dbconnect.cursor()
        sql = "SELECT message_hash FROM signature_verification WHERE message_hash = '" + message_hash + "'" 
        count = cursor.execute(sql)
        rs = cursor.fetchone()
        if rs == None:
        # Reuse check ok!
        # Now place an entry in the auth_pool table...
            sql = "INSERT INTO auth_pool(authorized_id) VALUES('" + id + "')"
            try:
                c = cursor.execute(sql)
                dbconnect.commit()
                cursor.close()
            except sqlite3.Error as error:
                print("Failed to insert session into the database.", error)
                exit(1)
            dbconnect.close()
# DAB 2023-07-10 - REMOVE hardcoded ID. Read it from the config file
            my_id = '498EM2vdJRSV6LcRUadS7TE4BdpusMz4wWMAm8YoBAw3M8D3ZkdvYSQN42FBm1aG7X8pRkEFpgvZBPAh78xbYLnj1NZbgJD'
   #         print("STARTING TO BUILD resource_message...")
            resource_message = '{"json":"2.0","method":"resource_message","params":{"id":"' + my_id + '"'
            challenge = str(secrets.randbelow(100000000))
            resource_id = buffer['params']['resource_id']
            for x in buffer['params']:
                if x != 'resource_mgr_id' and x != 'challenge_string' and x!= 'id' and x != 'signature':
                    try:
                        resource_message = resource_message + ',"' + x + '":"' + buffer['params'][x] + '"'
                    except:
                        resource_message = resource_message + ',"' + x + '":' + json.dumps(buffer['params'][x]) 

            resource_message = resource_message + ',"challenge_string":"' + challenge + '"'
            url = "http://127.0.0.1:18089/json_rpc"
            headers = {'content-type': 'application/json'}
# Now let's sign the challenge...
            rpc_input2 = {
                "method": "sign",
                "params": {"data": challenge,
                "account_index":0,
                "signature_type":"spend"}
                }
            rpc_input2.update({"jsonrpc": "2.0", "id": "0"})
            response2 = requests.post(url,data=json.dumps(rpc_input2),headers=headers)
            sd = response2.json()
            signature = sd["result"]["signature"]
            resource_message = resource_message + ',"signature":"' + signature + '"'
            seconds = time.time()
            epoch = str(seconds)
            resource_message = resource_message + ',"epoch":"' + epoch + '"}}'
            dbconnect = sqlite3.connect("/home/user/matrix-eno-bot/eno/scripts/resource_mgr")
            cursor = dbconnect.cursor()
            sql = "INSERT INTO signature_verification (message_hash, message) VALUES('" + message_hash + "','" + js + "')"
            count = cursor.execute(sql)
            dbconnect.commit()
            cursor.close()
            dbconnect.close()
            try:
                report_room = buffer['params']['room_id']
            except:
                report_room = room
            msg = buffer['params']['resource_id'] + " mprm " + resource_message
# DAB 2023-07-10 - Remove hardcoded directory structure below. Replace with config file values.
            com = "/home/user/.local/bin/matrix-commander --credentials /home/user/matrix-commander/credentials.json --store /home/user/matrix-commander/store -m '" + msg + "'" + " --room '" + report_room + "'"
            try:
                ret = subprocess.check_output(com, shell=True)
            except subprocess.CalledProcessError as e:
                print("Error launching matrix-commander")
                print(e.output)
                exit(1)
        else:
        # Message reuse detected!
            dbconnect.close()
            print("Message reuse is NOT allowed!")
