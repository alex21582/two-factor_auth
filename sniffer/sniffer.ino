#include "freertos/FreeRTOS.h"
#include "esp_wifi.h"
#include "esp_wifi_types.h"
#include "esp_system.h"
#include "esp_event.h"
#include "esp_event_loop.h"
#include "nvs_flash.h"
#include "driver/gpio.h"

#define ESPPL_MAC_LEN                    6
#define LED_GPIO_PIN                     2
#define WIFI_CHANNEL_SWITCH_INTERVAL  (500)
#define WIFI_CHANNEL_MAX               (13)

uint8_t ad1[6], ad2[6], ad3[6];
uint8_t level = 0, channel = 1;
const int8_t SENSITIVITY = -50;
const uint16_t Bicon = 0x0080;
const uint16_t Request = 0x0040;

static wifi_country_t wifi_country = {.cc = "CN", .schan = 1, .nchan = 13}; //Most recent esp32 library struct

typedef struct {
  unsigned frame_ctrl: 16;
  unsigned duration_id: 16;
  uint8_t addr1[6]; /* receiver address */
  uint8_t addr2[6]; /* sender address */
  uint8_t addr3[6]; /* filtering address */
  unsigned sequence_ctrl: 16;
  uint8_t addr4[6]; /* optional */
} wifi_ieee80211_mac_hdr_t;

typedef struct {
  wifi_ieee80211_mac_hdr_t hdr;
  uint8_t payload[0]; /* network data ended with 4 bytes csum (CRC32) */
} wifi_ieee80211_packet_t;

static esp_err_t event_handler(void *ctx, system_event_t *event);
static void wifi_sniffer_init(void);
static void wifi_sniffer_set_channel(uint8_t channel);
static const char *wifi_sniffer_packet_type2str(wifi_promiscuous_pkt_type_t type);
static void wifi_sniffer_packet_handler(void *buff, wifi_promiscuous_pkt_type_t type);

esp_err_t event_handler(void *ctx, system_event_t *event)
{
  return ESP_OK;
}

void wifi_sniffer_init(void)
{
  nvs_flash_init();
  tcpip_adapter_init();
  ESP_ERROR_CHECK( esp_event_loop_init(event_handler, NULL) );
  wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
  ESP_ERROR_CHECK( esp_wifi_init(&cfg) );
  ESP_ERROR_CHECK( esp_wifi_set_country(&wifi_country) ); /* set country for channel range [1, 13] */
  ESP_ERROR_CHECK( esp_wifi_set_storage(WIFI_STORAGE_RAM) );
  ESP_ERROR_CHECK( esp_wifi_set_mode(WIFI_MODE_NULL) );
  ESP_ERROR_CHECK( esp_wifi_start() );
  esp_wifi_set_promiscuous(true);
  esp_wifi_set_promiscuous_rx_cb(&wifi_sniffer_packet_handler);
}

void wifi_sniffer_set_channel(uint8_t channel)
{
  esp_wifi_set_channel(channel, WIFI_SECOND_CHAN_NONE);
}

bool maccmp(uint8_t *mac1, uint8_t *mac2) {
  for (int i = 0; i < ESPPL_MAC_LEN; i++) {
    if (mac1[i] != mac2[i]) {
      return false;
    }
  }
  return true;
}

void print_mac(uint8_t *mac, int8_t rssi) {
  printf("%02d,%02x:%02x:%02x:%02x:%02x:%02x\n",
         rssi, mac[0], mac[1], mac[2],
         mac[3], mac[4], mac[5]
        );
}

void wifi_sniffer_packet_handler(void* buff, wifi_promiscuous_pkt_type_t type) {

  const wifi_promiscuous_pkt_t *ppkt = (wifi_promiscuous_pkt_t *)buff;
  const wifi_ieee80211_packet_t *ipkt = (wifi_ieee80211_packet_t *)ppkt->payload;
  const wifi_ieee80211_mac_hdr_t *hdr = &ipkt->hdr;

  if (ppkt->rx_ctrl.rssi > SENSITIVITY) {
    if (hdr->frame_ctrl == Bicon) {
      return;
    }
    if (hdr->frame_ctrl == Request) {
      printf("%02d,%02x:%02x:%02x:%02x:%02x:%02x\n",
             ppkt->rx_ctrl.rssi, hdr->addr2[0], hdr->addr2[1], hdr->addr2[2],
             hdr->addr2[3], hdr->addr2[4], hdr->addr2[5]
            );
      return;
    }
    if (!(hdr->frame_ctrl & (1 << 8)) || !(hdr->frame_ctrl & (1 << 9))) {
      for (int i = 0; i < ESPPL_MAC_LEN; i++) {
        ad1[i] = hdr->addr1[i];
        ad2[i] = hdr->addr2[i];
        ad3[i] = hdr->addr3[i];
      }
      if (maccmp(ad1, ad2)) {
        print_mac(ad3, ppkt->rx_ctrl.rssi);
        return;
      }
      else if (maccmp(ad1, ad3)) {
        print_mac(ad2, ppkt->rx_ctrl.rssi);
        return;
      }
      else if (maccmp(ad2, ad3)) {
        ;
        print_mac(ad1, ppkt->rx_ctrl.rssi);
        return;
      }
      else {
        print_mac(ad1, ppkt->rx_ctrl.rssi);
        print_mac(ad2, ppkt->rx_ctrl.rssi);
        print_mac(ad3, ppkt->rx_ctrl.rssi);
        return;
      }
    }
  }
  else {
    Serial.print("-,-\n");
  }
}

// the setup function runs once when you press reset or power the board
void setup() {
  // initialize digital pin 5 as an output.
  Serial.begin(115200);
  delay(10);
  wifi_sniffer_init();
  pinMode(LED_GPIO_PIN, OUTPUT);
}

// the loop function runs over and over again forever
void loop() {
  //Serial.print("inside loop");
  //  delay(1000); // wait for a second

  if (digitalRead(LED_GPIO_PIN) == LOW)
    digitalWrite(LED_GPIO_PIN, HIGH);
  else
    digitalWrite(LED_GPIO_PIN, LOW);
  vTaskDelay(WIFI_CHANNEL_SWITCH_INTERVAL / portTICK_PERIOD_MS);
  wifi_sniffer_set_channel(channel);
  channel = (channel % WIFI_CHANNEL_MAX) + 1;
}
