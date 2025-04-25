#include <stdlib.h>
#include <stdio.h>
#include <stdbool.h>
#include "emulator.h"
#include "sr.h" //changed from gbn.c

/* ******************************************************************
   Selective Repeat protocol. Adapted from GBN implementation.

  add comments 
**********************************************************************/

#define RTT 16.0 
#define WINDOWSIZE 6
#define SEQSPACE 12 //sequence space must be at least 2*windowsize for Selective Repeat -> 
#define NOTINUSE (-1)

/* generic procedure to compute the checksum of a packet.  Used by both sender and receiver  
   the simulator will overwrite part of your packet with 'z's.  It will not overwrite your 
   original checksum.  This procedure must generate a different checksum to the original if
   the packet is corrupted.
   
   NOTE: this function doesn't need to change when transitioning from Go-Back-N to SR since 
   its utility is only to caclulate checksum, which is the same for both mechanisms. 
*/
int ComputeChecksum(struct pkt packet)
{
  int checksum = 0;
  int i;

  checksum = packet.seqnum;
  checksum += packet.acknum;
  for ( i=0; i<20; i++ ) 
    checksum += (int)(packet.payload[i]);

  return checksum;
}

bool IsCorrupted(struct pkt packet)
{
  if (packet.checksum == ComputeChecksum(packet))
    return (false);
  else
    return (true);
}
