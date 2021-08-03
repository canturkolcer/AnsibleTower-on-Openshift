# Owner: Canturk Olcer, 2020
# Altered from (c) 2017, Edward Nunez <edward.nunez@cyberark.com>'s cyberark AIM lookup plugin code'
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
DOCUMENTATION = """
    lookup: hashi_vault
    short_description: get secrets from HashiCorp API
    description:
      - get secrets from HashiCorp API
    options :
      url:
        description: HashiCorp Vault API URL
        required: True
      token:
        description: Access token to authenticate HashiCorp API
        required: True
      output:
        description: Output of the lookup plugin
        default: 'password'
"""
EXAMPLES = """
  curl -k -H "X-Vault-Token: <token>" \
    -H "X-Vault-Request: true" \
    -H "Content-Type: application/json" \
    -X GET \
    <url>

"""
RETURN = """
  password:
    description:
      - The actual value stored
"""
from ansible.plugins.lookup import LookupBase
from ansible.utils.display import Display
import requests

display = Display()
class HashiCorpPassword:
    def __init__(self, url=None, token=None, output=None, **kwargs):
        self.url = url
        self.token = token

        self.output = output

    def get(self):

        request_url = self.url
        request_header = {'X-Vault-Token': self.token,  'X-Vault-Request': 'true', 'Content-Type': 'application/json'}
        res = requests.get(
            request_url,
            headers=request_header,
            timeout=60,
            verify=False
        )

        if res.status_code == 500:
            res = requests.get(
                request_url,
                headers=request_header,
                timeout=60,
                verify=False
            )

        res.raise_for_status()
        return res.json()['data']['data']['password']

class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        display.vvvv("%s" % terms)
        if isinstance(terms, list):
            return_values = []
            for term in terms:
                display.vvvv("Term: %s" % term)
                hashicorp_conn = HashiCorpPassword(**term)
                return_values.append(hashicorp_conn.get())
            return return_values
        else:
            hashicorp_conn = HashiCorpPassword(**terms)
            result = hashicorp_conn.get()
            return result
