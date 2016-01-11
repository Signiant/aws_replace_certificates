"""
replace_cert.py

Simple certificate replacement for load balancers and EBS configurations.

Be careful if two certs have the same name but different paths!!!!

THIS SCRIPT DOES NOT SUPPORT CHANGING PATHS!!!!!!!!!

"""

import boto3, sys, re

def verify_certs_exist(source_cert, dest_cert):
    iam_client = boto3.client('iam')

    #Get server certificates
    certs = iam_client.list_server_certificates()
    source_exists = False
    dest_exists = False

    #Split cert name and take last element (the name of the cert), and see if it matches
    for item in certs['ServerCertificateMetadataList']:
        if item['ServerCertificateName'].split("/")[-1] == source_cert:
            source_exists = True
        if item['ServerCertificateName'].split("/")[-1] == dest_cert:
            dest_exists = True

    #Notify if they exist or error and exit if they dont
    if source_exists:
        print("Source certificate " + source_cert + " exists.")
    else:
        print("ERROR: Unable to found source certificate: " + source_cert)
        sys.exit(1)

    if dest_exists:
        print("Destination certificate " + dest_cert + " exists.")
    else:
        print("ERROR: Unable to found destination certificate: " + dest_cert)
        sys.exit(1)

def main(kwargs, args):

    #TODO: Change to false before production
    dry_run = False
    if "dry-run" in kwargs or "n" in kwargs:
        print("Dry run")
        dry_run = True

    #Assume the cert names are the only two "arguments" (argument is something that doesnt start with '-') 
    try:
        source_cert = args[0]
        dest_cert = args[1]
    except IndexError:
        print("You must specify a source cert name (from) and a destination cert name (to)")
        sys.exit(1)

    #Verify certs exist
    verify_certs_exist(source_cert, dest_cert)

    if not dry_run:
        print("!!!WARNING!!!") 
        print("This script could make very dangerous changes, and it's recommended to run it with a --dry-run (-n) to see what it will change before it does it.")
        response = raw_input("Please respond 'yes' if you understand the consequences: ")
        if response != "yes":
            print("Aborting changes.")
            sys.exit(1)
    
    #Get list of load balancers
    elb_client = boto3.client('elb')
    load_balancer_list = elb_client.describe_load_balancers()
    ebs_list = list()
        
    for lb in load_balancer_list["LoadBalancerDescriptions"]:

        #Describe tags takes a list with each load balancer name you want to look up
        lb_name = list()
        lb_name.append(lb["LoadBalancerName"])
        
        #Returns a dictionary
        response = elb_client.describe_tags(LoadBalancerNames=lb_name)

        #We need the TagDescriptions value, which is a list with one element (since we only passed in one name), and we need the Tags value
        tags = response["TagDescriptions"][0]["Tags"]
        name = None 
        ebs_name = None
        stack_name = None

        for tag in tags:
            if tag["Key"] == "Name":
                name = tag["Value"]
            if tag["Key"] == "elasticbeanstalk:environment-name":
                ebs_name = tag["Value"]
            if tag["Key"] == "aws:cloudformation:stack-name":
                stack_name = tag["Value"]

        if name is None:
            if ebs_name is not None:
                name = ebs_name
            else:
                name = stack_name

        #Drill down and make sure the listener is HTTPS protocol, make sure source_cert is part of the SSLCertificateId string, and replace that part with dest_cert
        for listener in lb["ListenerDescriptions"]:
            if listener["Listener"]["Protocol"] == "HTTPS":
                if source_cert == listener["Listener"]["SSLCertificateId"].split("/")[-1]:
                    replaced_string = re.sub(source_cert, dest_cert, listener["Listener"]["SSLCertificateId"])
                    print("Replacing " + listener["Listener"]["SSLCertificateId"] + " with " + replaced_string + " in loadbalancer: " + str(name))
                    if not dry_run:
                        pass
                    #Try to get the ebs name, if there is one for this load balancer
                    if ebs_name is not None:
                        ebs_list.append(ebs_name)

    for bs in ebs_list:
        print "Replacing " + source_cert + " with " + dest_cert + " in beanstalk: " + bs

#Modified From maestro
def parse_sysargs():
    current_key = None
    kwargs = dict()
    args = list()
    try:
        for arg in sys.argv[1:]:
            if current_key is None:
                if arg.startswith('-'):
                    current_key = arg.lstrip('-')
                else:
                    args.append(arg)
                continue
            if current_key is not None and not arg.startswith("-"):
                args.append(arg)
            else:
                kwargs[current_key] = None
                current_key = arg.lstrip('-')
        if current_key is not None and current_key not in kwargs:
            kwargs[current_key] = None
            current_key = None
    except IndexError:
        args.append(sys.argv[1])

    return kwargs, args


if __name__ == "__main__":
    kwargs, args = parse_sysargs()
    main(kwargs, args)
