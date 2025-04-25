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