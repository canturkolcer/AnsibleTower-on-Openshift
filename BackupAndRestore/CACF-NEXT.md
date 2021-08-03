- [Introduction](#introduction)
- [Backup CACF NEXT](#backup-cacf-next)
- [Restore CACF NEXT](#restore-cacf-next)

## Introduction
This procedure was prepared for a CACF NEXT deployment on Openshift 4.x platform.

Here there are the instructions how to export data from CACF NEXT and restore back.

<br>


## Backup CACF NEXT

1. [Optional] Change openshift project to next and scale down next deployment for a clean backup. Tested also without scaling down. No issues were detected.

    ```
    $ oc project next
    $ oc scale deployment next-api --replicas=0
    $ oc scale deployment next-resque --replicas=0
    $ oc scale deployment next-ui --replicas=0
    ```

2. Connect to next mysql container to find db paremeters

    ```
    % oc get pods
    NAME                                  READY   STATUS      RESTARTS   AGE
    next-api-xxx-yyy              1/1     Running     0          45h
    next-backup-xxx-yyy          0/1     Completed   0          7h58m
    next-cdi-collector-xxx-yyy   0/1     Completed   0          10h
    next-db-master-0                      1/1     Running     0          46h
    next-db-slave-0                       1/1     Running     0          45h
    next-redis-master-0                   1/1     Running     0          46h
    next-redis-slave-0                    1/1     Running     0          46h
    next-resque-xxx-yyy          1/1     Running     0          45h
    next-ui-xxx-yyy               1/1     Running     0          45h


    $ oc rsh next-db-master-0 
    1000550000@next-db-master-0:/$ env | grep MARIADB_PASSWORD
        MARIADB_PASSWORD=******  

    ```

3. Execute backup for CACF NEXT

    ```
    mysqldump --add-drop-table -h next-db -u next -p[MARIADB_PASSWORD from previous step] next > "/tmp/next-db-backup"
    ```

4. Download backup   
    ```
    $ oc cp next-db-master-0:/tmp/next-db-backup ./next-db-backup
    ```

## Restore CACF NEXT

1. Change openshift project to next and scale down next deployment.

    ```
    $ oc project next
    $ oc scale deployment next-api --replicas=0
    $ oc scale deployment next-resque --replicas=0
    $ oc scale deployment next-ui --replicas=0
    ```

2. Upload backup to the container. 

    ```
    % oc get pods
        NAME                                  READY   STATUS      RESTARTS   AGE
        next-api-xxx-yyy              1/1     Running     0          45h
        next-backup-xxx-yyy          0/1     Completed   0          7h58m
        next-cdi-collector-xxx-yyy   0/1     Completed   0          10h
        next-db-master-0                      1/1     Running     0          46h
        next-db-slave-0                       1/1     Running     0          45h
        next-redis-master-0                   1/1     Running     0          46h
        next-redis-slave-0                    1/1     Running     0          46h
        next-resque-xxx-yyy          1/1     Running     0          45h
        next-ui-xxx-yyy               1/1     Running     0          45h

    $ oc cp ./next-db-backup next-db-master-0:/tmp/next-db-backup 
    ```

3. Restore CACF NEXT.
    *** used output redirection here to keep the logs in case of any time out happens ***

    ```
    $ oc rsh next-db-master-0
    $ env | grep MARIADB_PASSWORD
        MARIADB_PASSWORD=******  
    $mysql -h next-db -u next -p[MARIADB_PASSWORD from above command] next < /tmp/next-db-backup
    ```

4. Scale up next.    
    ```
    $ oc scale deployment next-api --replicas=1
    $ oc scale deployment next-resque --replicas=1
    $ oc scale deployment next-ui --replicas=1
    ```
