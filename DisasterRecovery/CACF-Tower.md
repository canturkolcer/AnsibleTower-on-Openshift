- [Introduction](#introduction)
- [Building Disaster Recovery Environment](#building-disaster-recovery-environment)
- [Enable Disaster Recovery Site](#enable-disaster-recovery-site)
- [Enable Primary Site](#enable-primary-site)

## Introduction
This procedure was prepared for a CACF Ansible Tower disaster recovery structure on Openshift 4.x platform.

Here there are the instructions how to build DR structure and steps to perform in case of disaster and revert back to primary when needed.

Primary Site: primaryserver - 10.1.1.135
DR Site: drserver - 10.2.1.135
Automation User: user

<br>


## Building Disaster Recovery Environment

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

    # cat /opt/eregldap/uar/configure/protectedid.dat | grep user
    user
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
        # mkdir tower
    ```
    *** Used ACL here to let automation user has rigths to use the folder and content.

5. Created following backup [script](files/tower_backup.sh) at Primary Site and make sure it has execute permissions.

    ```
    #!/bin/bash

    # variables
    LOCAL_OCP_API_URL="https://api.oc4.cluster.local:6443"
    LOCAL_OCP_USER="kubeadmin"
    LOCAL_OCP_PASSWORD="*****"
    LOCAL_OCP_TOWER_PROJECT_NAME="tower"
    LOCAL_COPY_DIR="/ocp_dr/tower"
    LOCAL_LOG_DIR="/ocp_dr/tower"
    LOCAL_TIMESTAMP=$(date +"%Y-%m-%d-%H%M")

    DR_IP="10.2.1.135"
    DR_COPY_DIR="/ocp_dr/tower"
    DR_COPY_USER="user"
    DR_COPY_USER_SSHKEY="/home/user/.ssh/drsync_id_rsa"


    # backup block
    {
    # delete backups, older than 2 days
    find "$LOCAL_COPY_DIR" -name '*.db' -mtime +1 -delete
    find "$LOCAL_COPY_DIR" -name '*.log' -mtime +7 -delete

    echo "Backup is starting $LOCAL_TIMESTAMP"

    # Login to openshift
    echo Logging in to OCP
    /usr/local/bin/oc login -u "$LOCAL_OCP_USER" -p "$LOCAL_OCP_PASSWORD" "$LOCAL_OCP_API_URL" --insecure-skip-tls-verify

    # Change project to Ansible Tower project
    echo Switch to Ansible Tower project
    /usr/local/bin/oc project "$LOCAL_OCP_TOWER_PROJECT_NAME"

    # Find pod name of postgresql
    POD_NAME=`/usr/local/bin/oc get pods -o custom-columns=POD:.metadata.name --no-headers -l name=postgresql`
    echo "$POD_NAME"

    # Get Postgresql admin password
    ADMIN_PASSWORD=`/usr/local/bin/oc exec -i "$POD_NAME" -- bash -c 'env | grep POSTGRESQL_PASSWORD | cut -d "=" -f2'`
    echo "$ADMIN_PASSWORD"

    # create a backup
    echo Creating backup
    /usr/local/bin/oc exec -i "$POD_NAME" -- bash -c 'PGPASSWORD='"$ADMIN_PASSWORD"' pg_dump --clean --create -Fc -Z1 --host="postgresql" --username="admin" --dbname="tower"' > "$LOCAL_COPY_DIR"/tower_backup_"$LOCAL_TIMESTAMP".db

    # send backup to DR
    echo Sending backup to DR site
    scp -i "$DR_COPY_USER_SSHKEY" "$LOCAL_COPY_DIR"/tower_backup_"$LOCAL_TIMESTAMP".db "$DR_COPY_USER"@"$DR_IP":"$DR_COPY_DIR"/

    echo Backup Completed
    } > "$LOCAL_LOG_DIR"/tower_backup_"$LOCAL_TIMESTAMP".log 2>&1

    ```

6. Set crontab for user user on Primary site to take backup.
    - Primary Site:
    ```
    # DR Jobs
    0 1 * * * /ocp_dr/tower/tower_backup.sh
    ```

    ```

7. Create following entry to crontab of DR Site to delete old backups
   ```
   0 2 * * * find /ocp_dr/tower -name '*.db' -mtime +1 -delete
   ```
8. Deploy Ansible Tower according to documentation provided [here](../BackupAndRestore/AnsibleTower-OCP-Deployment.md) on DR Site.

9.  Deploy Customized lookup plugin on Ansible Tower as mentioned [here](../Customized-Lookup-Plugin-Installation-Configuration-and-Usage.md#deployment-of-customized-lookup-plugin-on-tower-pod).

10. After all pods are up and running DR environment is ready.


## Enable Disaster Recovery Site

In case of disaster, DNS should be switched to DR site and Ansible Tower should be restored with backup stored under /ocp_dr/tower directory using instructions [here](../BackupAndRestore/AnsibleTower.md#restore-ansible-tower)


## Enable Primary Site

When Primary site comes back, DNS will be switched after restore to Primary site will be completed. 

1. Scale down DR site deployment to prevent db to be written.
   ```
   # oc scale --replicas=0 deployment/ansible-tower
   ```

2. Take a backup of DR site as showed [here](../BackupAndRestore/AnsibleTower.md#backup-ansible-tower)

3. Send Backup to Primary site and restore as showed [here](../BackupAndRestore/AnsibleTower.md#restore-ansible-tower)

4. DNS switch can be done after Ansible Tower is reachable.
