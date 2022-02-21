**!! POC SOLUTION. THIS SOLUTION IS NOT ON PRODUCTION !!**
  
- [Introduction](#introduction)
- [Building Disaster Recovery Environment](#building-disaster-recovery-environment)
- [Enable Disaster Recovery Site](#enable-disaster-recovery-site)
- [Enable Primary Site](#enable-primary-site)

## Introduction
This procedure was prepared for a Ansible Tower disaster recovery structure on Openshift 4.x platform using CrunchyData Postgresql Operator.
Here there are the instructions how to build DR structure and steps to perform in case of disaster and revert back to primary when needed.

In this solution, S3 Buckets on OCS 4.6 is being used for DR replication.

** Prerequsites: 

- Openshift with OCS 4.6 or above is needed
- Firewall should be opened - if exists - from Primary site application worker nodes to DR site application load balancer for NodePort. 

<br>


## Building Disaster Recovery Environment

1. On DR Site in Openshift Storage project, set nodeport manually to the same value so in case needed Primary site can reach S3 bucket through NodePort. Service name is "s3" and port "s3-https nodePort is set to 31974.
   ```
    spec:
    ports:
        - name: s3
        protocol: TCP
        port: 80
        targetPort: 6001
        nodePort: 32575
        - name: s3-https
        protocol: TCP
        port: 443
        targetPort: 6443
        nodePort: 31974
        - name: md-https
        protocol: TCP
        port: 8444
        targetPort: 8444
        nodePort: 31814
   ```

2. Add NodePort to DR Application LoadBalancer to point OCS nodes only and restart haproxy.

    ```
    # vim /etc/haproxy/haproxy.conf
        frontend s3-nodeport-svc
        bind *:31974
        default_backend s3-nodeport-svc
        mode tcp
        option tcplog

        backend s3-nodeport-svc
        balance source
        mode tcp
        server ocsworker1 10.1.1.16:31974 check
        server ocsworker2 10.1.1.17:31974 check
        server ocsworker3 10.1.1.18:31974 check   
    #  systemctl restart haproxy       
    ```

3. Login to Noobaa Web Interface at DR site to create a bucket and user for Postgresql Operator. Url can be reachable from Google Chrome only. Access can be granted by using kubeadmin or any openshift admin userid.
    
    https://noobaa-mgmt-openshift-storage.apps.oc4.local.cluster/

4. Create a new account for operator to use and create new bucket with giving user access. Note down Access and Secret keys for postgresql configuration.
   
   ![here](files/noobaa_account_creation_1.png) 
   ![here](files/noobaa_account_creation_2.png)

5. Create a new project on DR site. For Primary site, installation will be done on already existing project.
   ```
   % oc create tower
   ```

6. Create a pull secret for CrunchyData repository.
   ```
   % oc create secret docker-registry crunchydata-pull-secret \
        --docker-username=<email> \
        --docker-password=<password> \
        --docker-server=registry.crunchydata.com \
        --namespace=<namespace>
        secret/crunchydata-pull-secret created
   ```

7. Prepare installation yaml files for deployment. Download or clone [postgresql-operator-samples](https://github.com/canturkolcer/postgres-operator-examples/tree/v5.0.0-alpha.4-0) from github and start editing yaml files. In this document, kustomize will be used to deploy operator and database.
8. Prepare operator deployment files. Files are located under kustomize/install/bases/ path. Following changes should be done on mentioned files.
    - Edit [kustomization.yaml](files/postgres-operator-examples/kustomize/install/bases/kustomization.yaml) file and use correct namespace and image tag
        ```
        % cat install/bases/kustomization.yaml
        namespace: tower

        commonLabels:
          postgres-operator.crunchydata.com/control-plane: postgres-operator

        bases:
        - crd
        - rbac/cluster
        - manager

        images:
        - name: postgres-operator
          newName: registry.crunchydata.com/crunchydata/postgres-operator
          newTag: ubi8-5.0.3-0

        ```
    - Edit [service_account.yaml](files/postgres-operator-examples/kustomize/install/bases/rbac/cluster/service_account.yaml) and add pull secret name.
        ```
        % cat install/bases/rbac/cluster/service_account.yaml
        ---
        apiVersion: v1
        kind: ServiceAccount
        metadata:
          name: pgo
        imagePullSecrets:
          - name: crunchydata-pull-secret
        ```
    - Edit [service_account.yaml](files/postgres-operator-examples/kustomize/install/bases/rbac/namespace/service_account.yaml) and add pull secret name.
        ```
        % cat install/bases/rbac/namespace/service_account.yaml
        ---
        apiVersion: v1
        kind: ServiceAccount
        metadata:
          name: pgo
        imagePullSecrets:
          - name: crunchydata-pull-secret
        ```        

9.  Deploy operator to the namespace.
    ```
    % oc apply -k install/bases
    customresourcedefinition.apiextensions.k8s.io/postgresclusters.postgres-operator.crunchydata.com configured
    serviceaccount/pgo created
    clusterrole.rbac.authorization.k8s.io/postgres-operator created
    clusterrolebinding.rbac.authorization.k8s.io/postgres-operator created
    deployment.apps/pgo created    
    ```

10. Prepare postgresql deployment files which uses S3 Buckets. Files are located under kustomize/s3/ path. Following changes should be done on mentioned files.
    - Edit [s3.conf](files/postgres-operator-examples/kustomize/s3/s3.conf) file and define s3 access key and secret key variables you gathered at step 4. Alternatively; you can navigate at noobaa web page to Buckets and than click Connect Application button. Be sure you selected correct account you created at step 4.
    - Edit [kustomization.yaml](files/postgres-operator-examples/kustomize/s3/kustomization.yaml) file. Correct namespace and s3 secret name.
    ```
    % cat kustomization.yaml 
        namespace: tower

        secretGenerator:
        - name: pgo-s3-creds-e1
          files:
          - s3.conf

        generatorOptions:
          disableNameSuffixHash: true

        resources:
        - postgres.yaml
    ```
    - Edit [postgres.yaml](files/postgres-operator-examples/kustomize/s3/postgres.yaml) file for database deployment settings.
    ```
    % cat postgres.yaml
    apiVersion: postgres-operator.crunchydata.com/v1beta1
    kind: PostgresCluster
    metadata:
      name: postgresql-tower
    spec:
      shutdown: false
      openshift: true
      dataSource:
        postgresqlCluster:
          clusterName: postgresql-tower
          repoName: repo1
      image: registry.crunchydata.com/crunchydata/crunchy-postgres:ubi8-10.18-5.0.3-0
      imagePullSecrets:
        - name: crunchydata-pull-secret
      postgresVersion: 10
      instances:
        - name: primary
          authentication:
            sslmode: 'prefer'
          resources:
            limits:
              memory: 32Gi
          dataVolumeClaimSpec:
            accessModes:
            - "ReadWriteOnce"
            resources:
              requests:
                storage: 500Gi
      users:
         - name: admin
           databases:
             - postgresql-tower
           options: "SUPERUSER"
      backups:
        pgbackrest:
           image: registry.crunchydata.com/crunchydata/crunchy-pgbackrest:ubi8-5.0.3-0
         repoHost:
           dedicated: {}
         configuration:
           - secret:
             name: pgo-s3-creds-e1
         global:
           repo1-path: /pgbackrest/postgres-operator/postgresql-tower-s3/repo1
           repo1-storage-verify-tls: "n"
           repo1-s3-uri-style: "path"
         repos:
           - name: repo1
         s3:
           bucket: "<Bucket name created at step 4>"
           endpoint: "<DR Site Application LoadBalancer IP : NodePort>"
           region: "<Region of Cloud resource>"

         patroni:
           dynamicConfiguration:
             postgresql:
               parameters:
                 archive_timeout: 60
             pg_hba:
               - "host all all all md5"
      standby:
        enabled: false
        repoName: repo1
    ```

    ** Last section should be set as following for DR instance
    ```
      standby:
        enabled: true
        repoName: repo1    
    ```

11. Deploy postgresql to Primary Site first
    ```
    % oc apply -k s3/
    secret/pgo-s3-creds-e1 created
    postgrescluster.postgres-operator.crunchydata.com/postgresql-tower created

    ``` 

12. Change admin user password to the one desired. Without this step passwords in Tower may not match. 
    Postgresql needs a verifier to set password manually. This [script](files/encrypt_password.py) will provide verifier which can be found at [github](https://gist.github.com/jkatz/e0a1f52f66fa03b732945f6eb94d9c21). Generated password should be encyrpt with base64.
    ```
    % python3 ./encrypt_password.py -u <username> -p <password>
    b'SCRAM-SHA-256$4096:******'

    % echo <value> | base64
    Use outputs above and update secret postgresql-tower-pguser-admin
    % oc patch secret -n tower-dr postgresql-tower-pguser-admin -p '{"data":{"password":"*****","verifier":"*****"}}'

    ```

13. Deploy Ansible tower with official method and use secret postgresql-tower-pguser-admin to fill database related parts.
    ```
    # Database Settings
    # =================

    # Set pg_hostname if you have an external postgres server, otherwise
    # a new postgres service will be created
    pg_hostname=<host variable from secret postgresql-tower-pguser-admin >

    # If using an external database, provide your existing credentials.
    # If you choose to use the provided containerized Postgres depolyment, these
    # values will be used when provisioning the database.
    pg_username='<user variable from secret postgresql-tower-pguser-admin >'
    pg_password='<password variable from secret postgresql-tower-pguser-admin >'
    pg_database=<dbname variable from secret postgresql-tower-pguser-admin >
    pg_port=5432
    pg_sslmode='prefer'  # set to 'verify-full' for client-side enforced SSL

    ```

14. Deploy Ansible tower on Primary instance.
    ```
    % ./setup_openshift.sh
    ```
    ** If environment has a http proxy no_proxy should be defined. Otherwise installation will fail.
    ```
    % export no_proxy=10.1.1.13,.oc4.local.cluster,10.0.0.0/8,127.0.0.1,localhost
    ```

15. Restore database for Primary if there is an backup.
16. With following same steps from Step 11 deploy DR Site as well. Do not restore db on DR. It will be restored by operator using S3 Bucket.
17. Make sure Ansible Tower on DR site is scaled down.
    ```
    % oc scale --replicas=0 deployment/ansible-tower
    ```
18. [OPTIONAL] To Check replication, connect to DR postgresql pod and postgresql database and check database content.
    ```
    # oc project tower-dr
    Now using project "tower-dr" on server "https://api.oc4.local.cluster:6443".
    # oc get pods
    NAME                                 READY   STATUS      RESTARTS   AGE
    pgo-55cf944576-pqt5m                 1/1     Running     0          3d
    postgresql-tower-backup-t974-5v6nh   0/1     Completed   0          2d1h
    postgresql-tower-primary-q959-0      2/2     Running     0          2d1h
    # oc rsh postgresql-tower-primary-q959-0
    Defaulting container name to database.
    Use 'oc describe pod/postgresql-tower-primary-q959-0 -n tower-dr' to see all of the containers in this pod.
    sh-4.4$ psql -h postgresql-tower-primary.tower-dr.svc -U admin -d postgresql-tower
    Password for user admin:
    psql (10.18)
    SSL connection (protocol: TLSv1.3, cipher: TLS_AES_256_GCM_SHA384, bits: 256, compression: off)
    Type "help" for help.

    postgresql-tower=# select * from auth_user where id=198;
    id  |                                    password                                    | last_login | is_superuser | username | first_name | last_name |        email        | is_st
    aff | is_active |          date_joined
    -----+--------------------------------------------------------------------------------+------------+--------------+----------+------------+-----------+---------------------+------
    ----+-----------+-------------------------------
    198 | ***** |            | f            | test-pr  | test-pr    |           | test-pr@example.com | f
        | t         | 2021-10-26 09:04:47.918091+00
    (1 row)

    ```
## Enable Disaster Recovery Site

In disaster case, Primary database will be lost. Postgresql on Dr site with Ansible tomwer should be set as primary manually.

1. Change DR postgresql yaml [file](files/postgres-operator-examples/kustomize/s3/postgres.yaml) and be sure Standby set to false.
   ```
        shutdown: false
        .....
         standby:
            enabled: false
            repoName: repo1     
   ```

2. Deploy settings.
   ```
   $ oc apply -k s3-dr/
   ```

3. Scale up Ansible Tower on DR Site.
   ```
   $ oc scale --replicas=1 deployment/ansible-tower
   ```

## Enable Primary Site

To prevent split brain; Primary site should be redeployed as standby and than promote as master after replication ends.

1. Delete PVC which has Primary DB data.
  ```
    % oc get pvc
        NAME                                   STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS                AGE
        postgresql-tower-primary-kn2l-pgdata   Bound    pvc-a18e60b5-0cd7-4776-8ad7-15b4abbfbed4   500Gi      RWO            ocs-storagecluster-cephfs   89m
    % oc delete pvc/postgresql-tower-primary-kn2l-pgdata
  ```

2. Deploy Primary postgresql as standby and wait for restore to be completed from S3 Bucket.

  ```
  % cat s3/postgres.yaml 
      shutdown: false
      .....
        standby:
          enabled: true
          repoName: repo1  
  % oc apply -k s3/
      secret/pgo-s3-creds-e1 unchanged
      postgrescluster.postgres-operator.crunchydata.com/postgresql-tower configured  
  ```
3. Postgresql pod logs can be checked to see if restore ended or not. Pod logs should have following entry "standby with lock"
  ```
  # oc project tower-dr
  Now using project "tower-dr" on server "https://api.oc4.local.cluster:6443".
  # oc get pods
  NAME                                 READY   STATUS      RESTARTS   AGE
  pgo-55cf944576-pqt5m                 1/1     Running     0          3d3h
  postgresql-tower-backup-t974-5v6nh   0/1     Completed   0          2d4h
  postgresql-tower-primary-q959-0      2/2     Running     0          2d4h

  # oc logs postgresql-tower-primary-q959-0 -c database 

  2021-10-26 09:31:32,166 INFO: bootstrap (without leader) in progress
  2021-10-26 09:31:32,395 INFO: replica has been created using pgbackrest
  2021-10-26 09:31:32,397 INFO: bootstrapped (without leader)
  2021-10-26 09:31:32,411 WARNING: Removing unexpected parameter=jit value=off from the config
  2021-10-26 09:31:32.618 UTC [154] LOG:  pgaudit extension initialized
  2021-10-26 09:31:32.618 UTC [154] LOG:  listening on IPv4 address "0.0.0.0", port 5432
  2021-10-26 09:31:32.618 UTC [154] LOG:  listening on IPv6 address "::", port 5432
  2021-10-26 09:31:32,618 INFO: postmaster pid=154
  2021-10-26 09:31:32.621 UTC [154] LOG:  listening on Unix socket "/tmp/postgres/.s.PGSQL.5432"
  2021-10-26 09:31:32.655 UTC [154] LOG:  redirecting log output to logging collector process
  2021-10-26 09:31:32.655 UTC [154] HINT:  Future log output will appear in directory "log".
  /tmp/postgres:5432 - rejecting connections
  /tmp/postgres:5432 - rejecting connections
  /tmp/postgres:5432 - rejecting connections
  /tmp/postgres:5432 - rejecting connections
  /tmp/postgres:5432 - accepting connections
  2021-10-26 09:31:35,726 INFO: establishing a new patroni connection to the postgres cluster
  2021-10-26 09:31:35,730 INFO: My wal position exceeds maximum replication lag
  2021-10-26 09:31:35,805 INFO: following a different leader because i am not the healthiest node
  2021-10-26 09:31:41,529 INFO: My wal position exceeds maximum replication lag
  2021-10-26 09:31:41,604 INFO: continue following the old known standby leader
  2021-10-26 09:31:41,607 WARNING: Removing invalid parameter `jit` from postgresql.parameters
  2021-10-26 09:31:41,607 INFO: No PostgreSQL configuration items changed, nothing to reload.
  2021-10-26 09:31:52,029 INFO: My wal position exceeds maximum replication lag
  2021-10-26 09:31:52,100 INFO: continue following the old known standby leader
  2021-10-26 09:32:02,166 INFO: promoted self to a standby leader by acquiring session lock
  2021-10-26 09:32:02,167 INFO: Lock owner: postgresql-tower-primary-q959-0; I am postgresql-tower-primary-q959-0
  2021-10-26 09:32:02,278 INFO: updated leader lock during changing primary_conninfo and restarting
  2021-10-26 09:32:02,505 INFO: closed patroni connection to the postgresql cluster
  2021-10-26 09:32:02.716 UTC [242] LOG:  pgaudit extension initialized
  2021-10-26 09:32:02.717 UTC [242] LOG:  listening on IPv4 address "0.0.0.0", port 5432
  2021-10-26 09:32:02.717 UTC [242] LOG:  listening on IPv6 address "::", port 5432
  2021-10-26 09:32:02,714 INFO: postmaster pid=242
  /tmp/postgres:5432 - no response
  2021-10-26 09:32:02.725 UTC [242] LOG:  listening on Unix socket "/tmp/postgres/.s.PGSQL.5432"
  2021-10-26 09:32:02.776 UTC [242] LOG:  redirecting log output to logging collector process
  2021-10-26 09:32:02.776 UTC [242] HINT:  Future log output will appear in directory "log".
  /tmp/postgres:5432 - rejecting connections
  /tmp/postgres:5432 - rejecting connections
  /tmp/postgres:5432 - accepting connections
  2021-10-26 09:32:04,781 INFO: Lock owner: postgresql-tower-primary-q959-0; I am postgresql-tower-primary-q959-0
  2021-10-26 09:32:04,782 INFO: establishing a new patroni connection to the postgres cluster
  2021-10-26 09:32:04,902 INFO: no action. I am (postgresql-tower-primary-q959-0) the standby leader with the lock
  2021-10-26 09:32:15,329 INFO: no action. I am (postgresql-tower-primary-q959-0) the standby leader with the lock
  2021-10-26 09:32:25,330 INFO: no action. I am (postgresql-tower-primary-q959-0) the standby leader with the lock
  2021-10-26 09:32:35,331 INFO: no action. I am (postgresql-tower-primary-q959-0) the standby leader with the lock
  2021-10-26 09:32:45,330 INFO: no action. I am (postgresql-tower-primary-q959-0) the standby leader with the lock

  ```