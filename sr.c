#include <stdlib.h>
#include <stdio.h>
#include <stdbool.h>
#include "emulator.h"
#include "sr.h" /*changed from gbn.c*/

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
#define SEQSPACE 12 /*sequence space must be at least 2*windowsize for Selective Repeat */
#define NOTINUSE (-1)

/* generic procedure to compute the checksum of a packet.  Used by both sender and receiver
   the simulator will overwrite part of your packet with 'z's.  It will not overwrite your
   original checksum.  This procedure must generate a different checksum to the original if
   the packet is corrupted.

   NOTE: this function doesn't need to change when transitioning from Go-Back-N to SR since
   its utility is only to calculate checksum, which is the same for both mechanisms.
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

/*  Firstly, implement side A, sending side */
static struct pkt buffer[WINDOWSIZE]; /* array for storing packets waiting for ACK */
static int windowfirst, windowlast;   /* array indexes of the first/last packet awaiting ACK */
static int windowcount;               /* the number of packets currently awaiting an ACK */
static int A_nextseqnum;              /* the next sequence number to be used by the sender */

static bool ACKed[WINDOWSIZE];     /* array to track which packets have been ACKed */

/* the following routine will be called once (only) before any other */
/* entity A routines are called. You can use it to do any initialization */
void A_init(void)
{
    int i;
    
    /* initialise A's window, buffer and sequence number */
    A_nextseqnum = 0; /* A starts with seq num 0, do not change this */
    windowfirst = 0;
    windowlast = -1; /* windowlast is where the last packet sent is stored.
             new packets are placed in winlast + 1
             so initially this is set to -1
           */
    windowcount = 0;

    /* initialize acked array */
    for (i = 0; i < WINDOWSIZE; i++)
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

                /* mark this packet as acked */
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
            else if (TRACE > 0)
                printf("----A: duplicate ACK received, do nothing!\n");
        }
    }
    else if (TRACE > 0)
        printf("----A: corrupted ACK is received, do nothing!\n");
}

/* called when A's timer goes off */
void A_timerinterrupt(void)
{
    if (TRACE > 0)
        printf("----A: time out,resend packets!\n");

    /* SR: Only resend the base packet, not the entire window as in GBN */
    if (windowcount > 0) {
        if (TRACE > 0)
            printf("---A: resending packet %d\n", buffer[windowfirst].seqnum);

        tolayer3(A, buffer[windowfirst]);
        packets_resent++;
        
        /* restart timer for this packet */
        starttimer(A, RTT);
    }
}

/********* Receiver (B)  variables and procedures ************/
/* the following routine will be called once (only) before any other */
/* entity B routines are called. You can use it to do any initialization */

static int B_nextseqnum;          /* the sequence number for the next packets sent by B */
static int receive_base;          /* base of the receiver window */
static bool received[WINDOWSIZE]; /* tracks which packets have been received */
static struct pkt recv_buffer[WINDOWSIZE]; /* buffer for out of order packet, SR component */

void B_init(void)
{
    int i;
    B_nextseqnum = 1;
    receive_base = 0;

    /* initialize received array */
    for (i = 0; i < WINDOWSIZE; i++)
    {
        received[i] = false;
    }
}

/* called from layer 3, when a packet arrives for layer 4 at B */
void B_input(struct pkt packet)
{
    struct pkt sendpkt;
    int i;
    int idx;
    int receive_end;
    bool in_window = false;
    int prev_end;
    int prev_start;
    bool in_prev_window = false;
    
    /* if not corrupted */
    if (!IsCorrupted(packet)) {
        if (TRACE > 0)
            printf("----B: packet %d is correctly received, send ACK!\n", packet.seqnum);
        packets_received++;
        
        /* Calculate window boundaries */
        receive_end = (receive_base + WINDOWSIZE - 1) % SEQSPACE;
        
        /* Check if packet is within receive window */
        if (receive_base <= receive_end) {
            in_window = (packet.seqnum >= receive_base && packet.seqnum <= receive_end);
        } else {
            /* Handle wrap-around case */
            in_window = (packet.seqnum >= receive_base || packet.seqnum <= receive_end);
        }
        
        if (in_window) {
            /* Calculate buffer position for this sequence number */
            idx = (packet.seqnum - receive_base);
            if (idx < 0) 
                idx += SEQSPACE;
            idx = idx % WINDOWSIZE;
            
            /* Store packet in buffer if not already received */
            if (!received[idx]) {
                received[idx] = true;
                recv_buffer[idx] = packet;
                
                /* Deliver consecutive packets in order */
                while (received[0]) {
                    /* deliver to receiving application */
                    tolayer5(B, recv_buffer[0].payload);
                
                    /* Shift window and update base */
                    receive_base = (receive_base + 1) % SEQSPACE;
                
                    /* Shift buffer - move all packets down by 1 */
                    for (i = 0; i < WINDOWSIZE - 1; i++) {
                        received[i] = received[i + 1];
                        recv_buffer[i] = recv_buffer[i + 1];
                    }
                
                    /* Clear the last slot */
                    received[WINDOWSIZE - 1] = false;
                }
            }
        } else {
            /* Packet outside window */
            prev_end = (receive_base - 1);
            if (prev_end < 0) 
                prev_end += SEQSPACE;
            
            prev_start = (prev_end - WINDOWSIZE + 1);
            if (prev_start < 0) 
                prev_start += SEQSPACE;
            
            if (prev_start <= prev_end) {
                in_prev_window = (packet.seqnum >= prev_start && packet.seqnum <= prev_end);
            } else {
                in_prev_window = (packet.seqnum >= prev_start || packet.seqnum <= prev_end);
            }
            
            if (!in_prev_window) {
                /* Packet is too far ahead - don't ACK */
                return;
            }
        }
        
        /* Send ACK for this packet (if we got here) */
        sendpkt.acknum = packet.seqnum;
    } else {
        /* Packet is corrupted */
        /*SR: When a corrupted packet is received, the receiver doesn't send an ACK at all
            This causes the sender to time out and retransmit only that specific packet*/
    if (TRACE > 0) 
      printf("----B: packet corrupted, no ACK sent!\n");
        return;
    }

    /* create ACK packet (same as GBN) */
  sendpkt.seqnum = B_nextseqnum;
  B_nextseqnum = (B_nextseqnum + 1) % 2;
    
  /* we don't have any data to send.  fill payload with 0's */
  for ( i=0; i<20 ; i++ ) 
    sendpkt.payload[i] = '0';  

  /* computer checksum */
  sendpkt.checksum = ComputeChecksum(sendpkt); 

  /* send out packet */
  tolayer3 (B, sendpkt);
}
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
