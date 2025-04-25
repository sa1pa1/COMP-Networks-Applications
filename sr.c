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

//Firstly, implement side A, sending side 
/********* Sender (A) variables and functions ************/
static struct pkt buffer[WINDOWSIZE];  /* array for storing packets waiting for ACK */
static int windowfirst, windowlast;    /* array indexes of the first/last packet awaiting ACK */
static int windowcount;                /* the number of packets currently awaiting an ACK */
static int A_nextseqnum;               /* the next sequence number to be used by the sender */

static bool ACKed[WINDOWSIZE];         /* array to track which packets have been ACKed */
static double packet_timer[WINDOWSIZE]; /* tracking the expiry timer for each packet */

/* the following routine will be called once (only) before any other */
/* entity A routines are called. You can use it to do any initialization */
void A_init(void)
{
  /* initialise A's window, buffer and sequence number */
  A_nextseqnum = 0;  /* A starts with seq num 0, do not change this */
  windowfirst = 0;
  windowlast = -1;   /* windowlast is where the last packet sent is stored.  
		     new packets are placed in winlast + 1 
		     so initially this is set to -1
		   */
  windowcount = 0;
  
  /* initialize acked array */
  for (int i = 0; i < WINDOWSIZE; i++) {
    ACKed[i] = false;
    packet_timer[i] = 0.0;
  }
}

/********* Receiver (B)  variables and procedures ************/
/* the following routine will be called once (only) before any other */
/* entity B routines are called. You can use it to do any initialization */

static int B_nextseqnum;   /* the sequence number for the next packets sent by B */
static int receive_base;       /* base of the receiver window */
static bool received[WINDOWSIZE]; /* tracks which packets have been received */

void B_init(void)
{
  B_nextseqnum = 1;
  receive_base = 0;
  
  /* initialize received array */
  for (int i = 0; i < WINDOWSIZE; i++) {
    received[i] = false;
  }
}
//incomplete
/******************************************************************************
 * The following functions need be completed only for bi-directional messages *
 *****************************************************************************/

/* Note that with simplex transfer from a-to-B, there is no B_output() */
void B_output(struct msg message)  
{
}

/* called when B's timer goes off */
void B_timerinterrupt(void)
{
}

