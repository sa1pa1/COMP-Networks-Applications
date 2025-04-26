#include <stdlib.h>
#include <stdio.h>
#include <stdbool.h>
#include "emulator.h"
#include "sr.h" //changed from gbn.c

/* ******************************************************************
   Selective Repeat protocol. Adapted from GBN implementation.

    Key differences from Go-Back-N:
   1. Receiver buffers out-of-order packets instead of discarding them
   2. Sender resends only specific unacknowledged packets, not entire window
   3. Individual ACKs for packets instead of cumulative acknowledgments
   4. Larger sequence number space (at least 2x window size)
**********************************************************************/

#define RTT 16.0
#define WINDOWSIZE 6
#define SEQSPACE 12 // sequence space must be at least 2*windowsize for Selective Repeat ->
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
    for (i = 0; i < 20; i++)
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

// Firstly, implement side A, sending side
/********* Sender (A) variables and functions ************/
static struct pkt buffer[WINDOWSIZE]; /* array for storing packets waiting for ACK */
static int windowfirst, windowlast;   /* array indexes of the first/last packet awaiting ACK */
static int windowcount;               /* the number of packets currently awaiting an ACK */
static int A_nextseqnum;              /* the next sequence number to be used by the sender */

static bool ACKed[WINDOWSIZE];          /* array to track which packets have been ACKed */

/* the following routine will be called once (only) before any other */
/* entity A routines are called. You can use it to do any initialization */
void A_init(void)
{
    /* initialise A's window, buffer and sequence number */
    A_nextseqnum = 0; /* A starts with seq num 0, do not change this */
    windowfirst = 0;
    windowlast = -1; /* windowlast is where the last packet sent is stored.
             new packets are placed in winlast + 1
             so initially this is set to -1
           */
    windowcount = 0;

    /* initialize acked array */
    for (int i = 0; i < WINDOWSIZE; i++)
    {
        ACKed[i] = false;
    }
}
/* called from layer 5 (application layer), passed the message to be sent to other side */
void A_output(struct msg message)
{
  struct pkt sendpkt;
  int i;

  /* if not blocked waiting on ACK */
  if ( windowcount < WINDOWSIZE) {
    if (TRACE > 1)
      printf("----A: New message arrives, send window is not full, send new messge to layer3!\n");

    /* create packet */
    sendpkt.seqnum = A_nextseqnum;
    sendpkt.acknum = NOTINUSE;
    for ( i=0; i<20 ; i++ ) 
      sendpkt.payload[i] = message.data[i];
    sendpkt.checksum = ComputeChecksum(sendpkt); 

    /* put packet in window buffer */
    /* windowlast will always be 0 for alternating bit; but not for GoBackN */
    windowlast = (windowlast + 1) % WINDOWSIZE; 
    buffer[windowlast] = sendpkt;
    ACKed[windowlast] = false;  /* SR: Mark new packet as not yet ACKed */
    windowcount++;

    /* send out packet */
    if (TRACE > 0)
      printf("Sending packet %d to layer 3\n", sendpkt.seqnum);
    tolayer3 (A, sendpkt);

    /* start timer if first packet in window */
    if (windowcount == 1)
      starttimer(A,RTT);

    /* get next sequence number, wrap back to 0 */
    A_nextseqnum = (A_nextseqnum + 1) % SEQSPACE;  
  }
  /* if blocked,  window is full */
  else {
    if (TRACE > 0)
      printf("----A: New message arrives, send window is full\n");
    window_full++;
  }
}

/* called from layer 3, when a packet arrives for layer 4 
   In this practical this will always be an ACK as B never sends data.
*/
void A_input(struct pkt packet)
{
    int ackcount = 0;
    int i;
    int index = -1;
    bool window_changed = false;

    /* if received ACK is not corrupted */
    if (!IsCorrupted(packet))
    {
        if (TRACE > 0)
            printf("----A: uncorrupted ACK %d is received\n", packet.acknum);
        total_ACKs_received++;

        /* check if new ACK or duplicate */
        if (windowcount != 0)
        {
            /* find which packet in window this ACK is for */
            for (i = 0; i < windowcount; i++)
            {
                int pos = (windowfirst + i) % WINDOWSIZE;
                if (buffer[pos].seqnum == packet.acknum)
                {
                    index = pos;
                    break;
                }
            }

            /* if we found the packet this ACK is for and it hasn't been ACKed yet */
            if (index != -1 && !ACKed[index])
            {

                /* packet is a new ACK */
                if (TRACE > 0)
                    printf("----A: ACK %d is not a duplicate\n", packet.acknum);
                new_ACKs++;

                // mark this packet as acked.
                ACKed[index] = true;

                while (windowcount > 0 && ACKed[windowfirst])
                {
                    /* SR: Slide window only when base packet is ACKed
                       In GBN, window slides based on highest ACK received
                       In SR, window slides incrementally past consecutive ACKed packets
                    */
                    ACKed[windowfirst] = false; /* reset for reuse */

                    windowfirst = (windowfirst + 1) % WINDOWSIZE;
                    windowcount--;
                    window_changed = true;
                }

                /* SR: Only reset timer if window position changed
                   In SR, we don't reset timer for every ACK received */
                if (window_changed)
                {
                    stoptimer(A);
                    if (windowcount > 0)
                        starttimer(A, RTT);
                }
            }
        }
        else if (TRACE > 0)
            printf("----A: duplicate ACK received, do nothing!\n");
    }
    else if (TRACE > 0)
        printf("----A: corrupted ACK is received, do nothing!\n");
}

/********* Receiver (B)  variables and procedures ************/
/* the following routine will be called once (only) before any other */
/* entity B routines are called. You can use it to do any initialization */

static int B_nextseqnum;          /* the sequence number for the next packets sent by B */
static int receive_base;          /* base of the receiver window */
static bool received[WINDOWSIZE]; /* tracks which packets have been received */

void B_init(void)
{
    B_nextseqnum = 1;
    receive_base = 0;

    /* initialize received array */
    for (int i = 0; i < WINDOWSIZE; i++)
    {
        received[i] = false;
    }
}
// incomplete
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
