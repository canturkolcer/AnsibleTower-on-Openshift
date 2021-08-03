1. Need to create private key pair for SAML authentication for tower
    ```
    % openssl genrsa -out tower\-samlCA.key 2048
    Generating RSA private key, 2048 bit long modulus
    .+++
    ...+++
    e is 65537 (0x10001)

    % openssl req -new -key tower\-samlCA.key -out tower\-samlCA.csr
    You are about to be asked to enter information that will be incorporated
    into your certificate request.
    What you are about to enter is what is called a Distinguished Name or a DN.
    There are quite a few fields but you can leave some blank
    For some fields there will be a default value,
    If you enter '.', the field will be left blank.
    -----
    Country Name (2 letter code) []:
    State or Province Name (full name) []:
    Locality Name (eg, city) []:
    Organization Name (eg, company) []:
    Organizational Unit Name (eg, section) []:
    Common Name (eg, fully qualified host name) []:
    Email Address []: <Mandatory Field>

    Please enter the following 'extra' attributes
    to be sent with your certificate request
    A challenge password []:

    % openssl x509 -req -in tower\-samlCA.csr -signkey tower\-samlCA.key -out tower\-samlCA.crt
    Signature ok
    subject=/emailAddress=canturk.olcer@pl.ibm.com
    Getting Private key
    ```

2. Create SAML configuration on tower and save. (Application PAth: settings -> authentication -> saml )


   ***SAML service provider entity id:*** <Tower URL>
   ***SAML Service Provider Public Certificate:*** <Created Above>
   ***SAML Service Provider Private Key:*** <Created Above>

   ***SAML Service Provider Organization Info:***
  ```
  {
   "en-US": {
    "url": "<Tower URL>",
    "name": "ansible-tower-web",
    "displayname": "ansible-tower"
   }
  }
  ```


  ***SAML Service Provider Technical Contact:***
  ```
  {
   "emailAddress": "canturk.olcer@pl.ibm.com",
   "givenName": "Canturk Olcer"
  }
  ```

  ***SAML Service Provider Support Contact:***
  ```
  {
   "emailAddress": "canturk.olcer@pl.ibm.com",
   "givenName": "Canturk Olcer"
 }
 ```

 ***SAML Enabled Identity Providers:***
 ```
  {
   "w3id": {
    "attr_username": "emailaddress",
    "attr_email": "emailaddress",
    "url": "https://login.w3.ibm.com/saml/sps/saml20ip/saml20/login",
    "entity_id": "https://w3id-prod.ice.ibmcloud.com/saml/sps/saml20ip/saml20",
    "x509cert": "get from saml page of IBM",
    "attr_user_permanent_id": "name_id",
    "attr_first_name": "firstName",
    "attr_last_name": "lastName"
   },
    "w3id-preprod": {
     "attr_username": "emailaddress",
     "attr_email": "emailaddress",
     "url": "https://preprod.login.w3.ibm.com/saml/sps/saml20ip/saml20/login",
     "entity_id": "https://w3id-prep.ice.ibmcloud.com/saml/sps/saml20ip/saml20",
     "x509cert": "get from saml page of IBM",
     "attr_user_permanent_id": "name_id",
     "attr_first_name": "firstName",
     "attr_last_name": "lastName"
    }
  }
  ```

  ***SAML Security Config:***
  ```
  {
   "logoutResponseSigned": true,
   "authnRequestsSigned": true,
   "requestedAuthnContext": true,
   "wantAssertionsSigned": true,
   "wantMessagesSigned": true,
   "logoutRequestSigned": true
  }
  ```

3. Download metafile for SAML configuration on IBM SSO Page. Copy ***SAML Service Provider Metadata URL*** to your browser and save as xml format.

4. Login to IBM SSO page and create a new application:

  ***IBM SSO PAGE URL:*** https://ies-provisioner.prod.identity-services.intranet.ibm.com/tools/sso/home

  - Create a new registration with "Register a w3id application" link.
  - Fill the first page as you wish.
  - Pick "Use w3id (BluePages) SAML 2.0." at next page
  - Pick w3id Production on IBM Security Verify (typical choice for most applications).
    ***Production needs one day to be created. Suggested to create prod and preprod (will be done in minutes), test connection on preprod.***
  - Target Application URL : <Tower URL>
  - Upload a Service Provider Metadata File you downloaded above.
  - Pick Challenge for 2FA every time - exceeds ITSS
  - Save.

5. After seeing success on SSO page, try to logout from your tower session and login with small S symbol at login page of Tower.
