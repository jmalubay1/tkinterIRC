import struct

"""
Sets the max packet size for transmission,
calculating the max payload length
"""
MAX_PACKET_SIZE = 2048

"""
Sets the Format for packing the header into the struct
The Size is based on the format so the packet can be properly
split into the header and payload

Current format is OPCODE - ushort (H), Payload Length - uint (I)  
"""
HEADER_FMT = '=HI'
HEADER_SIZE = struct.calcsize(HEADER_FMT)

"""
Opcode dictionary, codes are packed as unsigned shorts 2 bytes in size
up to 256 possible opcodes
"""
OPCODES = {
    "OPCODE_ERR": 0,
    "OPCODE_HELLO": 1,
    "OPCODE_GET_ROOMS": 2,
    "OPCODE_LIST_ROOMS": 3,
    "OPCODE_LIST_USERS": 4,
    "OPCODE_CREATE_ROOM": 5,
    "OPCODE_JOIN_ROOM": 6,
    "OPCODE_LEAVE_ROOM": 7,
    "OPCODE_SEND_MSG": 8,
    "OPCODE_BROADCAST_MSG": 9,
}

def getOpCode(num):
    for k,v in OPCODES.items():
        if num == v:
            return k
    return "OPCODE_UNKNOWN"

"""
Error code dictionary, codes are packed as unsigned shorts 2 bytes in size
up to 256 possible error codes
"""
ERROR_FMT = 'H'
ERROR_SIZE = struct.calcsize(ERROR_FMT)
ERRORCODES = {
    "ERR_UNKNOWN": 0,
    "ERR_ILLEGAL_OPCODE": 1,
    "ERR_ILLEGAL_LENGTH": 2,
    "ERR_NAME_EXISTS": 4,
    "ERR_ILLEGAL_NAME": 5,
    "ERR_ILLEGAL_MESSAGE": 6,
    "ERR_TOO_MANY_USERS": 7,
    "ERR_TOO_MANY_ROOMS": 8,
    "ERR_NOT_IN_ROOM": 9
}

def getErrCode(num):
    for k,v in ERRORCODES.items():
        if num == v:
            return k
    return "ERR_UNKNOWN"

def encodePacket(opCode, payload='0'):
    """
    Message struct contains the Header struct and
    the payload as a binary
    """
    # If OPCODE is invalid return an error
    if opCode not in OPCODES.values():
        return 'ERROR ENCODING PACKET - Illegal OPCODE provided'

    # Encode message and get its length
    msg_bin = encodePayload(payload)
    msg_size = len(msg_bin)

    # If payload exceeds packet size return an error
    if (msg_size + HEADER_SIZE) > MAX_PACKET_SIZE:
        return 'ERROR ENCODING PACKET - Payload excees Max Packet Size'

    # Encode Header
    header = encodeHeader(opCode,msg_size)

    # Dynamically get struct format from paylaod size
    msg_fmt = f'{HEADER_SIZE}s{msg_size}s'

    # Return fully encoded packet
    return struct.pack(msg_fmt, header, msg_bin)

def encodeHeader(opCode, length):
    """
    Header struct is 2 byte unsigned short 'H' for the opCode
    and a 4 byte unsigned int 'I' for the length of the payload

    Returns a binary of length HEADER_FMT with the opCode
    and payload length
    """
    return struct.pack(HEADER_FMT, opCode, length)

def encodePayload(payload):
    """
    Converts the payload binary string and returns it
    Assumes payload is a string or an error number
    """

    # Checks if the payload is either a string or a number
    # Strings are messages, numbers are Error codes
    if type(payload) == str:
        return payload.encode()
    else:
        return struct.pack(ERROR_FMT,payload)


def encodeError(code):
    """
    Error messages are a struct containing the Header struct
    and the error code as the payload

    Returns a binary with the Header and errCode
    """

    # Invalid codes will create an 'unknown' code
    errCode = code
    if code not in ERRORCODES.values():
        errCode = ERRORCODES["ERR_UNKNOWN"]

    # Construct the packet
    header = encodeHeader(OPCODES["OPCODE_ERR"],ERROR_SIZE)
    errorFormat = f'{HEADER_SIZE}s{ERROR_FMT}'

    return struct.pack(errorFormat, header, errCode)

def decodePacket(packet):    
    """
    Splits a packet into the opcode, payload length and 
    payload decodes them and returns them as a tuple
    (OPCODE, LENGTH, PAYLOAD)
    """
 
    # Decode the header and payload
    header, bin_pyld = struct.unpack(f'{HEADER_SIZE}s{len(packet)-HEADER_SIZE}s',packet)
    opCode, length = decodeHeader(header)

    # Verify OPCODE is valid
    if opCode not in OPCODES.values():
        return encodePacket(OPCODES["OPCODE_ERR"], ERRORCODES["ERR_ILLEGAL_OPCODE"])

    # Verify the length of the payload is valid
    if length != len(bin_pyld):
        return encodePacket(OPCODES["OPCODE_ERR"], ERRORCODES["ERR_ILLEGAL_LENGTH"])

    # Decode the payload
    payload = decodePayload(opCode,bin_pyld)

    return (opCode, length, payload)

def decodeHeader(header):
    """
    Converts the header from the binary string into
    a tuple of (ODCODE, PAYLOAD LENGTH)
    """
    return struct.unpack(HEADER_FMT, header)
   


def decodePayload(opCode, payload):
    """
    Using the OPCODE from the header returns the 
    decoded payload
    """

    if opCode == OPCODES["OPCODE_ERR"] and len(payload) == ERROR_SIZE:
        erCode = struct.unpack(ERROR_FMT,payload)
        return erCode[0] # Return the Error Code
    else:
        return payload.decode()

