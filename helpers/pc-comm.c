#include <stdio.h>
#include <fcntl.h>   /* File Control Definitions           */
#include <termios.h> /* POSIX Terminal Control Definitions */
#include <unistd.h>  /* UNIX Standard Definitions      */ 
#include <errno.h>   /* ERROR Number Definitions           */
#include <signal.h>
#include <string.h>
#include <stdint.h>

int open_serial(char *port, int baud);

int main(void)
{
    int tty = open_serial("/dev/ttyUSB1", B9600);
    uint8_t buff[256];   /* Buffer to store the data received              */
    int  n;    /* Number of bytes read by the read() system call */

    while (1) {
        n = read(tty, &buff, sizeof buff); 
        if (n > 0){
            //printf("-%d-\n ", n);
            for(int i=0;i<n;i++){   
                printf("%02x ", buff[i]);
            }
        }
        fflush(stdout);
    }
    return 0;
}

int open_serial(char *port, int baud)
{

    int fd = open( port, O_RDWR | O_NOCTTY);    

    if(fd == -1)                        /* Error Checking */
        printf("\n  Error! in Opening tty  ");

    struct termios SerialPortSettings;  /* Create the structure                          */

    tcgetattr(fd, &SerialPortSettings); /* Get the current attributes of the Serial port */

    /* Setting the Baud rate */
    cfsetispeed(&SerialPortSettings,B9600); /* Set Read  Speed as 115200                       */
    cfsetospeed(&SerialPortSettings,B9600); /* Set Write Speed as 115200                       */

    /* 8N1 Mode */2", B9600);
    uint8_t buff[256];   /* Buffer to store the d
    SerialPortSettings.c_cflag &= ~PARENB;   /* Disables the Parity Enable bit(PARENB),So No Parity   */
    SerialPortSettings.c_cflag &= ~CSTOPB;   /* CSTOPB = 2 Stop bits,here it is cleared so 1 Stop bit */
    SerialPortSettings.c_cflag &= ~CSIZE;    /* Clears the mask for setting the data size             */
    SerialPortSettings.c_cflag |=  CS8;      /* Set the data bits = 8                                 */

    SerialPortSettings.c_cflag &= ~CRTSCTS;       /* No Hardware flow Control                         */
    SerialPortSettings.c_cflag |= CREAD | CLOCAL; /* Enable receiver,Ignore Modem Control lines       */ 


    SerialPortSettings.c_iflag &= ~(IXON | IXOFF | IXANY);          /* Disable XON/XOFF flow control both i/p and o/p */
    SerialPortSettings.c_lflag &= ~(ICANON | ECHO | ECHOE | ISIG);  /* Non Cannonical mode                            */

    SerialPortSettings.c_oflag &= ~OPOST;/*No Output Processing*/

    /* Setting Time outs */
    SerialPortSettings.c_cc[VMIN] = 1; /* Read at least 1 character */
    SerialPortSettings.c_cc[VTIME] = 0; /* Wait indefinetly   */

    cfmakeraw(&SerialPortSettings);

    if((tcsetattr(fd,TCSANOW,&SerialPortSettings)) != 0) /* Set the attributes to the termios structure*/
        printf("\n  ERROR ! in Setting attributes");
    else
        printf("\n  Baud rate = 9600 StopBits = 1 Parity = none\n");

    /*------------------------------- Read data from serial port -----------------------------*/

    tcflush(fd, TCIFLUSH);   /* Discards old data in the rx buffer            */
    return fd;
}
