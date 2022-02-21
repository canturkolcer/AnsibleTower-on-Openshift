- [Introduction](#introduction)
- [Backup Openshift ETCD](#backup-openshift-etcd)
- [Restore Openshift ETCD](#restore-openshift-etcd)

## Introduction
This procedure was prepared for a automated backup of ETCD on Openshift 4.x platform.

<br>
Installation servers:
Primary Site: primaryserver - 10.1.1.135
DR Site: drserver - 10.2.1.135
Automation User: user

## Backup Openshift ETCD

1. Created ssh keys to connect DR site on Primary site. According to the security restrictions it should be using RSA - 2048

    ```
    $ pwd
    /home/user/.ssh

    $ ssh-keygen -t rsa -b 2048
    Generating public/private rsa key pair.
    Enter file in which to save the key (/home/user/.ssh/id_rsa): /home/user/.ssh/drsync_id_rsa
    Enter passphrase (empty for no passphrase):
    Enter same passphrase again:
    Your identification has been saved in /home/user/.ssh/drsync_id_rsa.
    Your public key has been saved in /home/user/.ssh/drsync_id_rsa.pub.
    The key fingerprint is:
    SHA256:6qeFmJAagLnry2tMZbd5S4dkffs0+no0nAEZuaOr74E user@primaryserver
    The key's randomart image is:
    +---[RSA 2048]----+
    |           .+    |
    |..         +     |
    |+       .   o    |
    |.. + . o . + .   |
    |o = . = S o + o  |
    | = . = *.o . B   |
    |=   o =E+.. = o  |
    |oo   . o.... o   |
    |.=o   o++o .+.   |
    +----[SHA256]-----+
    ```

2. Added ssh public key to DR Site automation user's authorized_keys file with 'from' information to limit access. Added user to eregldap protectedid fiel to prevent sysconf to delete.

    ```
    $ pwd
    /home/user/.ssh
    $ cat authorized_keys
    from="10.1.1.135" <SSH Public key created above>

    ```

3. Test connection from Primary to DR
   ```
   [user@primaryserver .ssh]$ ssh -i /home/user/.ssh/drsync_id_rsa 10.2.1.135
 
   ```

4. Create file structure on both servers.
   
    ```
        # lvcreate -L 30G -n lv_ocp_dr ocpvg
        WARNING: ext4 signature detected on /dev/ocpvg/lv_ocp_dr at offset 1080. Wipe it? [y/n]: n
        Aborted wiping of ext4.
        1 existing signature left on the device.
        Logical volume "lv_ocp_dr" created.

        # mkfs.ext4 /dev/mapper/ocpvg-lv_ocp_dr
        mke2fs 1.42.9 (28-Dec-2013)
        Filesystem label=
        OS type: Linux
        Block size=4096 (log=2)
        Fragment size=4096 (log=2)
        Stride=0 blocks, Stripe width=0 blocks
        1966080 inodes, 7864320 blocks
        393216 blocks (5.00%) reserved for the super user
        First data block=0
        Maximum filesystem blocks=2155872256
        240 block groups
        32768 blocks per group, 32768 fragments per group
        8192 inodes per group
        Superblock backups stored on blocks:
            32768, 98304, 163840, 229376, 294912, 819200, 884736, 1605632, 2654208,
            4096000

        Allocating group tables: done
        Writing inode tables: done
        Creating journal (32768 blocks): done
        Writing superblocks and filesystem accounting information: done

        # mkdir /ocp_dr

        # cat /etc/fstab | grep ocp_dr
        /dev/mapper/ocpvg-lv_ocp_dr /ocp_dr ext4 user_xattr,acl 1 2

        # mount /ocp_dr
        # cd /ocp_dr

        # chmod -R 700 /ocp_dr
        # setfacl -R -m u:user:rwx /ocp_dr
        # mkdir etcd
    ```
    *** Used ACL here to let automation user has rigths to use the folder and content.

5. [Backup script](files/etcd_backup.sh) is created on installation server which can reach master nodes.

    ```
    # cat /ocp_dr/etcd/etcd_backup.sh
        #!/bin/bash

        # variables
        LOCAL_OCP_API_URL="https://api.oc4.cluster.local:6443"
        LOCAL_OCP_USER="kubeadmin"
        LOCAL_OCP_PASSWORD="*****"
        LOCAL_LOG_DIR="/ocp_dr/etcd"
        LOCAL_TIMESTAMP=$(date +"%Y-%m-%d-%H%M")


        LOCAL_BACKUPDIR="/ocp_dr/etcd"
        REMOTE_BACKUPDIR="/var/home/core/backup/"
        REMOTE_USER="core"

        {
        # delete backups, older than 7 days
        find "$LOCAL_BACKUPDIR" -name '*.tar' -mtime +7 -delete

        # Login to openshift
        echo Logging in to OCP
        /usr/local/bin/oc login -u "$LOCAL_OCP_USER" -p "$LOCAL_OCP_PASSWORD" "$LOCAL_OCP_API_URL" --insecure-skip-tls-verify

        #Get a functional master-node
        echo Finding a master node to get backup
        MASTER_NODE=`/usr/local/bin/oc get node --selector='node-role.kubernetes.io/master' -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | grep -vE 'NotReady|SchedulingDisabled' | head -1`
        echo $MASTER_NODE

        #Create backupdirectoy on master node
        echo Creating backupdirectoy on master node
        ssh $REMOTE_USER@$MASTER_NODE "mkdir -p $REMOTE_BACKUPDIR"

        #Execute backup
        echo Backing up ETCD on master node
        ssh $REMOTE_USER@$MASTER_NODE "sudo /usr/local/bin/cluster-backup.sh $REMOTE_BACKUPDIR"

        #Create Tar file with backups
        echo Creating Tar file with backups
        ssh $REMOTE_USER@$MASTER_NODE "sudo tar -cvf $REMOTE_BACKUPDIR/etcd_backup_$LOCAL_TIMESTAMP.tar $REMOTE_BACKUPDIR/*"

        #Change ownership from root to core
        echo Changing ownership of etcd backup
        ssh $REMOTE_USER@$MASTER_NODE "sudo chown -R $REMOTE_USER $REMOTE_BACKUPDIR/etcd_backup_$LOCAL_TIMESTAMP.tar"

        #Copy to local machine and delete on remote host
        echo Copying to local machine and delete on remote host
        scp $REMOTE_USER@$MASTER_NODE:$REMOTE_BACKUPDIR/etcd_backup_$LOCAL_TIMESTAMP.tar $LOCAL_BACKUPDIR

        #Delete files from master node
        echo Deleting files from master node
        ssh $REMOTE_USER@$MASTER_NODE "sudo rm -Rf $REMOTE_BACKUPDIR"
        } > "$LOCAL_LOG_DIR"/etcd_backup_"$LOCAL_TIMESTAMP".log 2>&1

    ```

6. Add entry to crontab for user user
    ```
    0 0 * * * /ocp_dr/etcd/etcd_backup.sh

    ```

7. Set up incremental filesystem backup with 30 days retention as well to backup up /ocp_dr/etcd directory.

## Restore Openshift ETCD

1. Not Tested yet but instructions are here
   https://docs.openshift.com/container-platform/4.6/backup_and_restore/disaster_recovery/scenario-2-restoring-cluster-state.html