1. Create a new namespace on Openshift and switch to that project

  ```
  % # oc new-project tower
  Now using project "tower" on server "https://10.72.90.153:6443".

  ```

2. Create PVC with using UI or CLI

  ```
  size: 500Gi
  type: RWO
  storageclass: <your storage class name>
  name: postgresql
  ```

3. Download Ansible Tower setup for openshift. (Better to use same version with CACF image)

  https://releases.ansible.com/ansible-tower/setup_openshift/

4. Unzip setup and edit inventory file with relevant information

  ```
  # This will create or update a default admin (superuser) account in Tower
  admin_user=admin
  admin_password='<admin password - Generate as you wish>'

  # Tower Secret key
  # It's *very* important that this stay the same between upgrades or you will lose
  # the ability to decrypt your credentials
  secret_key='<secret - Generate as you wish>'

  # If using an external database, provide your existing credentials.
  # If you choose to use the provided containerized Postgres depolyment, these
  # values will be used when provisioning the database.
  pg_username='admin'
  pg_password='<postgre admin password - Generate as you wish>'
  pg_database='tower'
  pg_port=5432
  pg_sslmode='prefer'  # set to 'verify-full' for client-side enforced SSL

  rabbitmq_password='<MQ password - Generate as you wish>'
  rabbitmq_erlang_cookie='<MQ cookie key - Generate as you wish>'

  # Deploy into Openshift
  # =====================

  # openshift_host=https://openshift.example.com
  # openshift_skip_tls_verify=false
  # openshift_project=tower
  # openshift_user=admin
  # openshift_password=password
  openshift_host=https://<your openshift ip/hostname>:6443
  openshift_skip_tls_verify=true
  openshift_project=tower
  openshift_user=kubeadmin
  openshift_password=<kubeadmin password>
  ```

5. [OPTIONAL] Add tower hostname to local hosts file for after installation if you do not have DNS defined.

  Find your route on openshift
  ```
  % oc get route
      NAME                    HOST/PORT                                                     PATH   SERVICES                PORT   TERMINATION     WILDCARD
      ansible-tower-web-svc   ansible-tower-web-svc-tower.apps..<OCPDomainPrefix>.<BaseDomain>          ansible-tower-web-svc   http   edge/Redirect   None

  ```
  ```
  <worker loadbalancer ip> ansible-tower-web-svc-tower.apps.<OCPDomainPrefix>.<BaseDomain>
  ```

6. Run setup to install Ansible Tower on OCP

  ```
  ./setup_openshift.sh
  ```

7. If fails try again, connection speed may differ and since it is a ansible setup file it will skip tasks which were done already.

8. Login to the tower and define your license, before proceed.

9. Be sure your tower and postgresql pods are in running state

  ```
  % oc get pods
    NAME                                   READY   STATUS      RESTARTS   AGE
    ansible-tower-f5f5d58bd-59vh4          4/4     Running     0          29d
    postgresql-1-65gqd                     1/1     Running     0          73d

  ```

10. [OPTIONAL] If you have proxy in your environment; Login to tower with admin user and password you defined in inventory and set proxy settings.

  Settings -> Jobs -> Extra Environment Variables
  ```
  {
   "HOME": "/var/lib/awx",
   "GIT_SSL_NO_VERIFY": "True",
   "HTTPS_PROXY": "http://<Proxy IP>",
   "https_proxy": "http://<Proxy IP>",
   "HTTP_PROXY": "http://<Proxy IP>",
   "http_proxy": "http://<Proxy IP>",
   "NO_PROXY": ".<OCPDomainPrefix>.<BaseDomain>,10.0.0.0/8,127.0.0.1,localhost",
   "no_proxy": ".<OCPDomainPrefix>.<BaseDomain>,10.0.0.0/8,127.0.0.1,localhost",
   "ANSIBLE_SCP_IF_SSH": "True",
   "ANSIBLE_TIMEOUT": "60"
  }
  ```

11. Check the version you will install from CACF webpage.
  ```
  https://w3.ibm.com/w3publisher/cacf-release-notes/release-versions
  ```
12. Login to artifactory and create a token for your user:
  https://eu.artifactory.swg-devops.com and navigate to Edit Profile and create an API key.

13. Create secret on openshift and link it with your tower deployment

  ```
  $ oc create secret docker-registry cacf-repo-pull-secret --docker-server=gts-cacf-global-team-prod-docker-local.artifactory.swg-devops.com --docker-username=<your user> --docker-password=<api key> --docker-email=<user email>
  $ oc secrets link awx cacf-repo-pull-secret --for=pull
  ```

14. Edit your deployment, change image url to golden image and save it (it is a vi window so to save it use <ESC>wq!):

  ```
  $ oc edit deployment/ansible-tower
  .....
  spec:
    containers:
      - image: gts-cacf-global-team-prod-docker-local.artifactory.swg-devops.com/tower/3.7.0:20.6.1
        imagePullPolicy: Always
        name: ansible-tower-web

  .....
    image: gts-cacf-global-team-prod-docker-local.artifactory.swg-devops.com/tower/3.7.0:20.6.1
    imagePullPolicy: Always
    name: ansible-tower-task
  .....    

  ```

15. Wait for your pods to running again.

  ```
  % oc get pods
    NAME                                   READY   STATUS      RESTARTS   AGE
    ansible-tower-f5f5d58bd-59vh4          4/4     Running     0          29d
    postgresql-1-65gqd                     1/1     Running     0          73d

  ```
