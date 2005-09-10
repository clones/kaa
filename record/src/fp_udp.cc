Filter_UDP::Filter_UDP( const std::string &host, int port ) 
{
    buffer.reserve(DEFAULT_MAX_BUFFERSIZE);

    /* create socket */
    if((sfd = socket(AF_INET,SOCK_DGRAM, 0)) == -1) {
	perror("socket");
	exit(1);
    }
  
    /* sender */
    sender.sin_family = AF_INET;
    sender.sin_addr.s_addr = htonl(INADDR_ANY);
    sender.sin_port = htons(0);

    if(bind(sfd, (struct sockaddr *)&cliAddr, sizeof(cliAddr)) < 0) {
      perror("bind");
      exit(1);
    }

    /* set the ttl */
    if(setsockopt(sfd, IPPROTO_IP, IP_MULTICAST_TTL, 1, sizeof(int)) < 0) {
      perror("cannot set ttl");
      exit(1);
    }

    /* sender */
    receiver.sin_family = AF_INET;
    receiver.sin_addr.s_addr = htonl(INADDR_ANY);
    receiver.sin_port = htons(port);
}

    
Filter_UDP::~Filter_UDP(){
    close(sfd);
}

Filter_UDP::add_data( const std::string &data ) 
{
    buffer.append( data );
}


Filter_UDP::void process_data() 
{
    if (buffer.length()) {
	sendto(sfd, buffer_in.c_str(), buffer.length(), 0, ipaddr, len(ipaddr));
	buffer.clear();
    }
}

std::string Filter_UDP::get_data() 
{
    return "";
}

