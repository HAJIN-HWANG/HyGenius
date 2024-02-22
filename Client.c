#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <bcm2835.h>
#include <pigpio.h>

#define SERVER_IP "10.3.141.227"
//define SERVER_IP "172.20.10.2"
#define SERVER_PORT 9000
#define BUZZER_PIN 18
#define PWM_RANGE 1000
#define PWM_FREQUENCY 1000
#define DUTY_CYCLE 500
#define VALVE_PIN 17 // 밸브 핀 번호
#define VALVE_OPEN 1
#define VALVE_CLOSE 0


int read_mcp3208_adc(unsigned char adcChannel)
{
   unsigned char tx_buff[6];
   unsigned char rx_buff[6];
   int adcValue=0;

   if (!bcm2835_init())
   {
       printf("bcm2835_init failed\n");
       return -1;
   }

   bcm2835_spi_chipSelect(BCM2835_SPI_CS0);
   bcm2835_spi_begin();

   tx_buff[0]=0x06 | ((adcChannel & 0x07) >> 7);
   tx_buff[1]=((adcChannel & 0x07) << 6);
   tx_buff[2]=0x00;

   bcm2835_spi_transfernb(tx_buff, rx_buff, 3);

   rx_buff[1]=0x0F & rx_buff[1];
   adcValue=(rx_buff[1] << 8) | rx_buff[2];

   bcm2835_spi_end();
   bcm2835_close();

   return adcValue;
}

int main(void)
{
    int sock;
    struct sockaddr_in server_addr;
    char message[256];
    int adcChannel;
    int adcValue = 0;
    double Ia, Va;
    int gasValue = 0;
    unsigned int buzzerDelay = 1;
    unsigned int sensorDelay = 100000;

    if (gpioInitialise() < 0) {
        printf("gpioInitialise failed\n");
        return 1;
    }

    gpioSetMode(BUZZER_PIN, PI_OUTPUT);
    gpioSetPWMrange(BUZZER_PIN, PWM_RANGE);
    gpioSetPWMfrequency(BUZZER_PIN, PWM_FREQUENCY);
    
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = inet_addr(SERVER_IP);
    server_addr.sin_port = htons(SERVER_PORT);

    sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock == -1) {
        perror("socket()");
        return -1;
    }

    if (connect(sock, (struct sockaddr*)&server_addr, sizeof(server_addr)) == -1) {
        perror("connect()");
        return -1;
    }

    while (1) {
        adcChannel = 0x00;
        adcValue = adcValue = read_mcp3208_adc(adcChannel);
        Ia = ((((5.0 / 4096) * adcValue) - 2.5 - 0.0099284) / 0.1);

        adcChannel = 0x01;
        adcValue = read_mcp3208_adc(adcChannel);
        Va = (int32_t)(((5.0 / 4096) * adcValue - 2.5 + 0.0123723) * 500);

        adcChannel = 0x02;
        adcValue = read_mcp3208_adc(adcChannel);
        gasValue = adcValue;

        snprintf(message, sizeof(message), "%10.7f, %10.7f, %d\n", Ia, Va, gasValue);

        if (send(sock, message, strlen(message), 0) == -1) {
            perror("send()");
            break;
        }

  
        if (gasValue >= 1700){
            gpioWrite(BUZZER_PIN, 1);

            
            
            gpioPWM(BUZZER_PIN, DUTY_CYCLE);
            // 가스 값이 1700을 넘으면 밸브를 닫음
            gpioWrite(VALVE_PIN, VALVE_CLOSE);
        }
        else {
        
        gpioWrite(BUZZER_PIN, 0);
        
            // 가스 값이 1700을 넘지 않으면 밸브를 열림
        gpioWrite(VALVE_PIN, VALVE_OPEN);
        
        
        }

        gpioDelay(sensorDelay);
    }
    bcm2835_close();
    close(sock);

    return 0;
}
