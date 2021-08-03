# -----------------------
# Owner: Canturk Olcer, 2020
# Altered from (c) 2017, Edward Nunez <edward.nunez@cyberark.com>
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type
DOCUMENTATION = """
    lookup: custompassword.py
    version_added: "1.1"
    short_description: get secrets from CyberArk AIM and HashiCorp Vault
    requirements:
      - Plugin should be added to repository under same directory with main playbook to be run with following directory structure :  lookup_plugins > custompassword.py 
      - Or pluning should be copied under python virtual environment on ansible task server/container with following structure: venv/ansible_ibm/lib/python2.7/site-packages/ansible/plugins/lookup/custompassword.py
    description:
      - get secrets from CyberArk AIM and HashiCorp Vault
    parameters :
      cred_provider:
        description: Credential provider name: cyberark | hashicorp
        required: True
      hashi_url:
        description: Hashicorp api url including version and following "/".
        required: True
      hashi_username:
        description: User created on hashicorp vault to access needed key-value search engine.
        required: True                
      hashi_password: 
        description: Passwords to authenticate hashicorp vault to get token for gathering password
        required: True
      vault_url_path: 
        description: Path to KV. Example: automation/data/windows/hostname
        required: True
      cya_url: 
        description: Cyberark AIM URL
        required: True        
      cya_app_id: 
        description: Cyberark AIM Application id for vault
        required: True
      cya_query: 
        description: Cyberark query to be sent to AIM
        required: True   
      cya_priv_key:     
        description: Certificate private key to secure connection 
        required: True      
      cya_cert_chain: 
        description: Certificate Chain to secure connection
        required: True               
      output:
        description:
          - Specifies the desired output fields separated by commas.
          - "They could be: Password, PassProps.<property>, PasswordChangeInProcess"
        default: 'password'
"""
EXAMPLES = """

ansible_password: |-
   {{ lookup("custompassword", {
           "cred_provider": "{{ cred_provider }}",
           "hashi_url": "{{ hashicorp_baseurl }}",
           "hashi_username": "{{ hashicorp_user }}",
           "hashi_password": "{{ hashicorp_password }}",
           "vault_url_path": "{{ vault_url_path }}",
           "cya_url": "{{ vars.get('cya_url_' ~ datacenter ) }}",
           "cya_app_id": "{{ cya_app_id }}",
           "cya_query": "{{ cya_query }}",
           "cya_priv_key": "{{ lookup('env', 'cya_priv_key_file') }}",
           "cya_cert_chain": "{{ lookup('env', 'cya_cert_file') }}",           
           } ) }}

"""
RETURN = """
  password:
    description:
      - The actual value stored
"""
import os
from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
from ansible.utils.display import Display
from urllib import urlencode
from urlparse import urljoin
import requests

display = Display()

class HashiCorpPassword:
    def __init__(self, hashi_url=None, vault_url_path=None, hashi_username=None, hashi_password=None, **kwargs):
        self.base_url = hashi_url 
        self.username = hashi_username
        self.password = hashi_password
        self.vault_url_path = vault_url_path

    def get(self):

        # Get token for query
        request_url = self.base_url + "auth/userpass/login/" + self.username
        
        res = requests.post(
          request_url,
          data='{"password": "' + self.password + '"}',
          timeout=60,
          verify=False
        )
        
        #Get password for server
        client_token = res.json()['auth']['client_token']
        
        request_url = self.base_url + self.vault_url_path
        request_header = {'X-Vault-Token': client_token,  'X-Vault-Request': 'true', 'Content-Type': 'application/json'}
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
            
        if res.status_code == 404:
            return ""    

        res.raise_for_status()
        return res.json()['data']['data']['password']
    
class CyberarkPassword:
    def __init__(self, cya_url=None, cya_app_id=None, cya_query=None, cya_object_query_format="Exact", cya_priv_key=None, cya_cert_chain=None, output=None, **kwargs):
        
        self.url = cya_url
        self.app_id = cya_app_id
        self.cya_query = cya_query
        self.object_query_format = cya_object_query_format
        self.cya_priv_key = cya_priv_key
        self.cya_cert_chain = cya_cert_chain
        self.output = output

    def get(self):            
        query_params = {
            'AppId': self.app_id,
            'Query': self.cya_query,
            'QueryFormat': self.object_query_format,
        }
        
        request_qs = '?' + urlencode(query_params)
        request_url = urljoin(self.url, '/'.join(['AIMWebService', 'api', 'Accounts']))    

        res = requests.get(
            request_url + request_qs,
            timeout=60,
            verify=False,
            cert=(self.cya_cert_chain, self.cya_priv_key)
        )         
        
        if res.status_code == 500:
          res = requests.get(
              request_url + request_qs,
              timeout=60,
              verify=False,
              cert=(self.cya_cert_chain, self.cya_priv_key)
          ) 
            
        display.vvvv("Display result of cya query: %s" % res.json() )
            
        if res.status_code == 404:
            return ""      
            
        res.raise_for_status()
        return res.json()['Content']
        
class LookupModule(LookupBase):
    """
    USAGE:
    """
    def run(self, terms, variables=None, **kwargs):
        display.vvvv("Display passed params: %s" % terms)
        provider = terms[0]['cred_provider']

        if isinstance(terms, list):
            return_values = []
            for term in terms:
                if provider == 'hashicorp':
                  hashicorp_conn = HashiCorpPassword(**term)
                  return_values.append(hashicorp_conn.get())
                elif provider == 'cyberark':
                  cyberark_conn = CyberarkPassword(**term)
                  return_values.append(cyberark_conn.get())
            
            return return_values
        else:
            if provider == 'hashicorp':
              hashicorp_conn = HashiCorpPassword(**terms)
              result = hashicorp_conn.get()
            elif provider == 'cyberark':
              cyberark_conn = CyberarkPassword(**terms)
              result = cyberark_conn.get()
         
            return result
