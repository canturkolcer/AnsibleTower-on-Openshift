- [Introduction](#introduction)
- [Backup Ansible Tower](#backup-ansible-tower)
- [Restore Ansible Tower](#restore-ansible-tower)

## Introduction
This procedure was prepared for an ansible tower deployment on Openshift 4.x platform.

Environment has approx. 200Gi postgresql db size. Official backup and restore procedure of ansible tower is using pg_dump to extract dump from database and than archive it.
This method needs large space and time to back up.

Also, offical restore method extract this archive created during backup, extracts that file and restores using psql command. This also needs time to extract and also restore.

According to our tests, official method takes 3 hours to backup and 3+ hours to restore our tower db from an external server in the same VLAN and openshift client deployed.

The method described below uses pg_dump and pg_restore, using around 20Gi disk space and ~1 hour backup / 2.5 hours restore time. Testeed dozen times so secure. 

Also, To improve restore performance you may need to tweak your postgresql memory settings. Restore spends most of its time on creating main_jobevent table and creating indexes for it. To increase memory of postgresql; edit deployment config of postgresql and change following according to your resources. 
```
...
- resources:
    limits:
        memory: 32Gi
...
- name: MEMORY_LIMIT
    value: 30Gi        
```    


<br>


## Backup Ansible Tower

1. [Optional] Change openshift project to ansible tower and scale down Ansible tower deployment for a clean backup. Tested also without scaling down. No issues were detected.

    ```
    $ oc project tower
    $ oc scale deployment ansible-tower --replicas=0
    ```

2. Connect to tower postgresql container to find db password. It can be also found at inventory file used during the first deployment

    ```
    $ oc get pods
    NAME                             READY   STATUS      RESTARTS   AGE
    ansible-tower-xxx-yyy   4/4     Running     0          19h
    postgresql-1-zzz               1/1     Running     0          19h

    $ oc rsh postgresql-1-zzz
    sh-4.2$ env | grep POSTGRESQL_PASSWORD
    POSTGRESQL_PASSWORD=*****

    ```

3. Execute backup for Ansible Tower

    ```
    oc exec -i postgresql-1-zzz -n tower -- bash -c 'PGPASSWORD="*****" pg_dump --clean --create -Fc -Z1 --host="postgresql" --username="admin" --dbname="tower"' > tower.db
    ```
   *** Important parameters of backup command ***
    - Z: This points degree of compression. 200Gi databses 20Gi backup file with compression level 1. It also affects restoring time so better to use as less as possible.

4. [Optional] Scale up tower if it was scaled down at first step.    
    ```
    $ oc scale deployment ansible-tower --replicas=1
    ```

## Restore Ansible Tower

1. Change openshift project to ansible tower scale down Ansible tower and postgresql deployments.

    ```
    $ oc project tower
    $ oc scale deployment ansible-tower --replicas=0
    $ oc scale deploymentconfig postgresql --replicas=0
    ```

2. Delete and recreate postgresql PVC if exists. Web UI can be used.

    ```
    $ oc delete pvc/postgresql

    $ oc get pvc/postgresql -o yaml
        apiVersion: v1
        kind: PersistentVolumeClaim
        metadata:
        name: postgresql
        namespace: tower
        spec:
        accessModes:
        - ReadWriteOnce
        resources:
            requests:
            storage: 500Gi
        storageClassName: ocs-storagecluster-cephfs
        volumeMode: Filesystem

    ```


3. Scale up postgresql deployment and copy backup to postgresql container. 
    *** 'oc exec' can be used like back up here but during restore there are creating index steps which makes connection idle until it is done. oc command will get timeout and restore will get broken. ***

    ```
    $ oc scale deploymentconfig/postgresql --replicas=1
    $ oc get pods
        NAME                             READY   STATUS      RESTARTS   AGE
        ansible-tower-xxx-yyy   4/4     Running     0          19h
        postgresql-1-zzz               1/1     Running     0          19h

    $ oc cp tower.db postgresql-2-zzz:/tmp/tower.db    
    ```

2) Restore Ansible Tower.
    *** used output redirection here to keep the logs in case of any time out happens ***

    ```
    PGPASSWORD="*****" pg_restore -v -j 10 --host="postgresql" -p "5432" --username="admin" --dbname="tower" --clean /tmp/tower.db >restore.log 2>&1
    ```
    *** Important parameters of backup command ***
     - j: number of jobs will run in parallel
     - p: PostgreSQL service port. Can be found on postgresql container
        ```
        $ env | grep POSTGRESQL_SERVICE_PORT
        POSTGRESQL_SERVICE_PORT_POSTGRESQL=5432
        POSTGRESQL_SERVICE_PORT=5432
        ```
3. Scale up tower.    
    ```
    $ oc scale deployment ansible-tower --replicas=1
    ```
