- [Introduction](#introduction)
- [Backup Secure File Service](#backup-secure-file-service)
- [Restore Secure File Service](#restore-secure-file-service)

## Introduction
This procedure was prepared for a CACF Secure File Service deployment on Openshift 4.x platform.

Here there are the instructions how to export data from CACF Secure File Service and restore back without losing creation dates of files.

<br>


## Backup Secure File Service

1. Change your project to secure-file-service.

    ```
    $ oc project secure-file-service
    ```

2. Connect to sfs-secure-file-service container and compress folders needs to be backed up.

    ```
      oc get pods
        NAME                                              READY   STATUS      RESTARTS   AGE
        sfs-backup-xxx-wsvjn                       0/1     Completed   0          8h
        sfs-secure-file-service-xxx-yyy        1/1     Running     0          15d
        sfs-secure-file-service-ui-xxx-yyy   1/1     Running     0          15d

    $ oc rsh sfs-secure-file-service-xxx-yyy
    sh-4.2$ tar -czvf  /tmp/sfs_backup.tar.gz /var/files

    ```

3. Download backup

    ```
    oc cp sfs-secure-file-service-xxx-yyy:/tmp/sfs_backup.tar.gz ./sfs_backup.tar.gz
    ```

## Restore Secure File Service

1. Change your project to secure-file-service.

    ```
    $ oc project secure-file-service
    ```
2. Upload backup to the container.

    ```
    oc cp ./sfs_backup.tar.gz sfs-secure-file-service-xxx-yyy:/tmp/sfs_backup.tar.gz
    ```

3. Restore backup with extracting file.

    ```
      oc get pods
        NAME                                              READY   STATUS      RESTARTS   AGE
        sfs-backup-xxx-wsvjn                       0/1     Completed   0          8h
        sfs-secure-file-service-xxx-yyy        1/1     Running     0          15d
        sfs-secure-file-service-ui-xxx-yyy   1/1     Running     0          15d

    $ oc rsh sfs-secure-file-service-xxx-yyy
    sh-4.2$ tar -xzvf /tmp/sfs_backup.tar.gz -C /var/files

    ```

