# CACF-Ansible-Tower-Upgrade-with-Customizations

  - [CACF-Ansible-Tower-Upgrade-with-Customizations](#cacf-ansible-tower-upgrade-with-customizations)
    - [Introduction](#introduction)
    - [Upgrade Ansible Tower with CACF Golden Image](#upgrade-ansible-tower-with-cacf-golden-image)

## Introduction
  Upgrading Ansible Tower on Openshift 4.x with customizations
  In this document, there are steps should be followed when upgrading Ansible tower with CACF Golden Image and customizations done for customer.

  It is suggested to do following steps on a server with same vlan so network wont be a bottleneck.

  ** PLEASE DO NOT FORGET TO CHECK CACF DOCUMENTATION BEFORE UPGRADE. EXTRA STEPS SHOULD BE REQUEIRED !!! **

  References:<br>
  https://github.ibm.com/cacf/cacf_docs/tree/gh-pages/cacf-release_notes/Release-Documents-21.2.0<br>


  Topology:

  * Openshift version 4.x
  * Ansible Tower 3.7

  <br>

## Upgrade Ansible Tower with CACF Golden Image

1. Check customizations are exist on openshift project. Please refer to following documentations and get familiar with customizations.
   
    - [Customized Lookup Plugin](Customized-Lookup-Plugin-Installation-Configuration-and-Usage.md)

2. Scale down pod count to 1 from Deployment using gui or with command.
    ```
      oc scale deployment ansible-tower --replicas=1
    ```

3. Get backup of Tower db, pod and deployment to a server. 

    To backup Ansible Tower please refer to [backup instructions](AnsibleTower.md)

    To backup of configuration:

    ```
    # oc get pod ansible-tower-f5f5d58bd-qkfln -o yaml >ansible-tower-0-pod.yaml
    # oc get deployment ansible-tower -o yaml >ansible-tower-deployment.yaml
    ```

4. Download new installer of your version from redhat and extract that.

    https://releases.ansible.com/ansible-tower/setup_openshift/

5. Copy inventory from following localtion or one of your old deployments. In case you lost and could not find; please refer to CACF documentation.
  
    https://github.ibm.com/cacf/cacf_docs/blob/gh-pages/cacf-release_notes/Release-Documents-21.2.0/CACF-Tower-Install%26Upgrade-21.2.0.docx
  

6. Run ./setup_openshift.sh to install new tower.
    * in case running from a server with http_proxy defined. you may need to add oc ip to no_proxy
    ```
    # export no_proxy=10.72.90.153,.oc4,10.0.0.0/8,127.0.0.1,localhost
    ```

7. Edit ConfigMap and set following variables to have right number of forks on each tower instance:
   
    ```
    # oc edit configmap ansible-tower-config
    .....
      SYSTEM_TASK_ABS_CPU = 12
      SYSTEM_TASK_ABS_MEM = 240
    .....
    ```
    
8. Update golden image and customizations at deployment. When save and exit, tower pods will restart automatically.
    ```
    # oc edit deployment ansible-tower
    ```

    - Update redhat tower iamge with CACF golden image. (exists in 2 places) 

    ```
    registry.redhat.io/ansible-tower-37/ansible-tower-rhel7:3.7.3 -> gts-cacf-global-team-prod-docker-local.artifactory.swg-devops.com/tower/3.7.4:21.2
    ```

    - Create new Volume for lookup plugin customization. Find "volumes" section and append following lines. **Be Careful with Indentiation**
    ```
          - name: custom-cred-lookup-plugin
            configMap:
              name: custom-cred-lookup-plugin
              defaultMode: 360
    ```

    - Create volume mount to container named "ansible-tower-task". Find "volumeMounts" section and append following lines. **Be Careful with Indentiation**
    ```
              - name: custom-cred-lookup-plugin
                mountPath: >-
                  /usr/lib/python2.7/site-packages/ansible/plugins/lookup/custompassword.py
                subPath: custompassword.py
    ```
    **Important Note :** Please get familiar with custom plugin before using above line: [Customized Lookup Plugin](Customized-Lookup-Plugin-Installation-Configuration-and-Usage.md)

    - Increase CPU and Memory for ansible-tower-task container to have more resources for each tower instance
    ```
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
    ```

9.  Run ping playbook to proove connections are working as expected.

10. Scale up Tower deployment to previous value.
    ```
    oc scale deployment ansible-tower --replicas=4
    ```