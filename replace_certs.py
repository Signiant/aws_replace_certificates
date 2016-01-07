"""
replace_cert.py

Simple certificate replacement for load balancers and EBS configurations.

Be careful if two certs have the same name but different paths!!!!

"""

import boto3, sys, re

def verify_certs_exist(source_cert, dest_cert):
    iam_client = boto3.client('iam')
    certs = iam_client.list_server_certificates()
    source_exists = False
    dest_exists = False

    for item in certs['ServerCertificateMetadataList']:
        if item['ServerCertificateName'].split("/")[-1] == source_cert:
            source_exists = True
        if item['ServerCertificateName'].split("/")[-1] == dest_cert:
            dest_exists = True

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

    #TODO: Change to false before publishing
    dry_run = True
    if "dry-run" in kwargs or "n" in kwargs:
        print("Dry run")
        dry_run = True
    try:
        source_cert = args[0]
        dest_cert = args[1]
    except IndexError:
        print("You must specify a source cert name (from) and a destination cert name (to)")
        sys.exit(1)

    verify_certs_exist(source_cert, dest_cert)

    elb_client = boto3.client('elb')
    load_balancer_list = elb_client.describe_load_balancers()
    ebs_list = list()
        
    for lb in load_balancer_list["LoadBalancerDescriptions"]:

        #Describe tags takes a list
        lb_name = list()
        lb_name.append(lb["LoadBalancerName"])
        
        #Returns a dictionary
        response = elb_client.describe_tags(LoadBalancerNames=lb_name)

        #We need the TagDescriptions value, which is a list with one element, and we need the Tags value
        tags = response["TagDescriptions"][0]["Tags"]

        for listener in lb["ListenerDescriptions"]:
            if listener["Listener"]["Protocol"] == "HTTPS":
                if source_cert in listener["Listener"]["SSLCertificateId"]:
                    print("Replacing " + source_cert + " with " + dest_cert + " in " + lb_name[0])
                    replaced_string = re.sub(source_cert, dest_cert, listener["Listener"]["SSLCertificateId"])
                    if not dry_run:
                        print "changes!!!!!"
                    #Try to get the ebs name, if there is one for this load balancer
                    try:
                        print str(tags)
                        ebs_list.append(tags[0]["elasticbeanstalk:environment-name"])
                    except KeyError:
                        pass

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
                #kwargs[current_key] = arg
                args.append(arg)
                #current_key = None
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