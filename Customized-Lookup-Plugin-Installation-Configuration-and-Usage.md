# Customized-Lookup-Plugin-Installation-Configuration-and-Usage

  - [Introduction](#introduction)
  - [How Customized Lookup Plugin Works](#how-customized-lookup-plugin-works)
  - [Deployment of Customized Lookup Plugin on Tower Pod](#deployment-of-customized-lookup-plugin-on-tower-pod)
  - [Credential Type and Credential Definition](#credential-type-and-credential-definition)
  - [Usage Examples](#usage-examples)

## Introduction

In this document, customized ansible lookup plugin for hashicorp vault and cyberark has been explained. Solution build for Ansible Tower implementaion running on Openshift 4.x. 

Ansible Tower has already plugin's for hasicorp vault and cyberark but the purpose here is to merge them into one so end user does not need to know which provider to use. On the other hand, standard ansible hashicorp plugin could not be used because we are using in-house created image which does not have HVAC module installed. Also, Image does not have cyberark cli so AIM method is needed to be used.

References:<br>

Topology:

* Openshift version 4.3
* Ansible Tower 3.7

<br>

## How Customized Lookup Plugin Works

Lookup plugin is a perl code consists 2 classes, HashiCorpPassword and CyberarkPassword. Plugin needs parameters to be deliver to get password from correct provider. All parameters are set on host variable level in our environment because that is up to host configuration. It can be defined anywhere else.

Parameters and definitions:
  - cred_provider: Selection of provider. Can be "hashicorp" or "cyberark"
  - hashi_url: Hashicorp api url including version and following "/". Example: https://hashicorp.apps.oc4/v1/
  - hashi_username: User created on hashicorp vault to access needed key-value search engine.
  - hashi_password: Passwords to authenticate hashicorp vault to get token for gathering password
  - vault_url_path: Path to KV. Example: automation/data/windows/hostname
  - cya_url: Cyberark AIM URL
  - cya_app_id: Cyberark AIM Application id for vault
  - cya_query: Cyberark query to be sent to AIM
  - cya_priv_key: Certificate private key to secure connection
  - cya_cert_chain: Certificate Chain to secure connection

If provider is Hashicorp; plugin will use username and password to get token for next query. Hashicorp does not have any method to query using username and password. Query will be sent with token to gather password to hashicorp. In case of HTTP 500 (Internal Server Error) script will try again. In case script gathers HTT 404 it will return empty string.

If provider is Cyberark; plugin will use certificate chain and private key to authenticate Cyberark AIM. Query path will be used to gether password. In case of HTTP 500 (Internal Server Error) script will try again. In case script gathers HTT 404 it will return empty string.

## Deployment of Customized Lookup Plugin on Tower Pod

1. Create a config map to store script.

    Lookup plugin script is store at [here](files/custompassword.py)
    ```
    % oc create configmap custom-cred-lookup-plugin --from-file=files/custompassword.py
    configmap/custom-cred-lookup-plugin created
    ```

2. Edit Tower Deployment, create following entries and save.
    ```
    # oc edit deployment ansible-tower
    ```

    - Create new Volume for lookup plugin customization. Find "volumes" section and append following lines. <br>
      **Be Careful with Indentiation**
    ```
          - name: custom-cred-lookup-plugin
            configMap:
              name: custom-cred-lookup-plugin
              defaultMode: 360
    ```

    - Create volume mount to container named "ansible-tower-task". Find "volumeMounts" section and append following lines. 
      Path should be your virtual environment path you want to add your plugin. Here it is used as "ansible_ibm".<br>
      **Be Careful with Indentiation**
    ```
              - name: custom-cred-lookup-plugin
                mountPath: >-
                  /usr/lib/python2.7/site-packages/ansible/plugins/lookup/custompassword.py
                subPath: custompassword.py
    ```

3. Tower pod(s) will restart automatically after saving. 

## Credential Type and Credential Definition

Credential Type has been defined to provide needed parameters easily and in a secure way. Credential type definition is:

  - Input Configuration:
    ```
    fields:
      - id: hashicorp_baseurl
        type: string
        label: Hashicorp Vault Api Base Url
      - id: hashicorp_kvname
        type: string
        label: Hashicorp Vault Key Value Engine name
      - id: hashicorp_user
        type: string
        label: Hashicorp Vault User Name
      - id: hashicorp_password
        type: string
        label: Hashicorp Vault User Password
        secret: true
      - id: cya_url_e1
        type: string
        label: E1 Cyberark AIM URL
      - id: cya_url_e2
        type: string
        label: E2 Cyberark AIM URL
      - id: cya_url_na1
        type: string
        label: NA1 Cyberark AIM URL
      - id: cya_url_na2
        type: string
        label: NA2 Cyberark AIM URL
      - id: cya_app_id
        type: string
        label: Cyberark Application ID
      - id: cya_priv_key
        type: string
        label: Cyberark Private Key
        format: ssh_private_key
        secret: true
        multiline: true
      - id: cya_cert
        type: string
        label: Cyberark Certificate
        multiline: true
      - id: jh1_ip_e1
        type: string
        label: E1 Jumphost1 IP Address
      - id: jh1_ip_e2
        type: string
        label: E2 Jumphost1 IP Address
      - id: jh1_ip_na1
        type: string
        label: NA1 Jumphost1 IP Address
      - id: jh1_ip_na2
        type: string
        label: NA2 Jumphost1 IP Address
      - id: jh1_ssh_user
        type: string
        label: Username to login with ssh in jumphost1
      - id: jh1_ssh_private_key
        type: string
        label: SSH Private Key for Jumphost1
        format: ssh_private_key
        secret: true
        multiline: true
      - id: jh1_ssh_port
        type: string
        label: SSH port for Jumphost1
      - id: jh_socks_port
        type: string
        label: Port on localhost to map with Jumphost1 port for socks5 proxy
    required:
      - hashicorp_baseurl
      - hashicorp_user
      - hashicorp_password
      - hashicorp_kvname
      - cya_url_e1
      - cya_url_e2
      - cya_url_na1
      - cya_url_na2
      - cya_app_id
      - cya_priv_key
      - cya_cert
      - jh1_ip_e1
      - jh1_ip_e2
      - jh1_ip_na1
      - jh1_ip_na2
      - jh1_ssh_user
      - jh1_ssh_private_key
      - jh1_ssh_port
      - jh_socks_port
    ```
  - Injector Configuration:
    ```
    env:
      JH1_SSH_PRIVATE_KEY: '{{tower.filename.jh1_ssh_private_key}}'
      cya_cert_file: '{{ tower.filename.cya_cert }}'
      cya_priv_key_file: '{{ tower.filename.cya_priv_key }}'
    extra_vars:
      cya_app_id: '{{ cya_app_id }}'
      cya_url_e1: '{{ cya_url_e1 }}'
      cya_url_e2: '{{ cya_url_e2 }}'
      cya_url_na1: '{{ cya_url_na1 }}'
      cya_url_na2: '{{ cya_url_na2 }}'
      hashicorp_baseurl: '{{ hashicorp_baseurl }}'
      hashicorp_kvname: '{{ hashicorp_kvname }}'
      hashicorp_password: '{{ hashicorp_password }}'
      hashicorp_user: '{{ hashicorp_user }}'
      jh1_ip_e1: '{{ jh1_ip_e1 }}'
      jh1_ip_e2: '{{ jh1_ip_e2 }}'
      jh1_ip_na1: '{{ jh1_ip_na1 }}'
      jh1_ip_na2: '{{ jh1_ip_na2 }}'
      jh1_ssh_port: '{{ jh1_ssh_port }}'
      jh1_ssh_user: '{{ jh1_ssh_user }}'
      jh_socks_port: '{{ jh_socks_port }}'
    file:
      template.cya_cert: '{{ cya_cert }}'
      template.cya_priv_key: '{{ cya_priv_key }}'
      template.jh1_ssh_private_key: '{{ jh1_ssh_private_key }}'

    ```

Credentials can be creted on this type and if used in template; one credential can have all variables to connect endpoint including jumphost information.    

## Usage Examples

### Prerequisites
- Following variables should be defined as variables. Depending on the best approach for client, we used host variables to store hsot realted information. Such as:
  ```
  ansible_user: < user ansible will use to connect endpoint >
  datacenter: < datacenter information to identify where server is located >
  devicetype: compute
  ansible_host: < Ip address to use while reaching server >
  tier: production
  ostype: < linux|aix|windows according to the endpoint OS >
  fqdn: < Server hostname >
  cred_provider: < Credential provider will be used: cyberark|hashicorp >
  alz_fqdn: < Customer hostname >
  ipaddress: < server ip address >
  ```

- Job Template should have a credential created based on Credential Type mentioned above.

### Using Inventory/Host/Group Variables

All variables can be defined as inventory variables. In this method, playbook will prepare everyhting according to the running host. Good for multiple
 hosts even mixed operation systems and credential providers.
  ```
blueid_shortcode: ao1

cred_provider: "{{ hostvars[inventory_hostname]['cred_provider'] }}"
fqdn: "{{ hostvars[inventory_hostname]['fqdn'] }}"
alz_fqdn: "{{ hostvars[inventory_hostname]['alz_fqdn'] }}"
ostype: "{{ hostvars[inventory_hostname]['ostype'] }}"
datacenter: "{{ hostvars[inventory_hostname]['datacenter'] }}"
ansible_user: "{{ hostvars[inventory_hostname]['ansible_user'] }}"

ansible_connection: "{{ 'psrp' if ostype == 'windows' else 'ssh' }}"

ansible_psrp_protocol: http
ansible_psrp_proxy: >-
    socks5h://unixsocket/tmp/mysocks-{{ account_code }}-{{ trans_num }}-{{ jh_socks_port }}-{{ datacenter }}

ansible_ssh_common_args: >-
    -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o
    ProxyCommand="ssh -W %h:%p {{ jh1_ssh_user }}@{{ vars.get('jh1_ip_' ~ datacenter ) }} -i
    $JH1_SSH_PRIVATE_KEY -o StrictHostKeyChecking=no -o
    UserKnownHostsFile=/dev/null"

shortOsType: "{{ ostype[:3] | upper }}"
cya_query: "{{ 'Object=' + shortOsType + '-' + alz_fqdn + '-' + ansible_user }}"
vault_url_path: "{{ hashicorp_kvname + '/data/' + ostype + '/' + fqdn }}"

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
  ```

### Ad-Hoc Queries inside playbooks

This approach can be used in case to connect some host not in playbook scope or if there are any other credential stored in vaults. Value of each variable can be gathered any possible method developer will decide.

Example:
```
  vars:
    ansible_password: {{ lookup("custompassword", {
              "cred_provider": "cyberark",
              "hashi_url": "none",
              "hashi_username": "none",
              "hashi_password": "none",
              "vault_url_path": "none",
              "cya_url": "10.10.10.1",
              "cya_app_id": "AppId",
              "cya_query": "Object=SYM-symantec.automation-symantec",
              "cya_priv_key": "/tmp/private.key",
              "cya_cert_chain": "/tmp/chain_cert.pem" } ) }}

```