# コーヒーポットIoT
## ファイル説明
### ラズパイ側
1. coffee_mon.py ... 歪センサーの値を、外部サーバにアップロードするデーモン

2. hx711.py ... HX711と通信し、歪センサーの値を取得（coffee_mon.pyから呼ばれる）

### 外部サーバ側
1. coffee-upd.cgi ... coffee_mon.py からのデータを受け取るCGI（データはPostgreSQLに保存）

2. coffee-mon.cgi ... PCやスマートフォンから、残量を表示するCGI

## 設置手順
1. ラズパイに coffee_mon.py と hx711.py を置き、起動時に coffee_mon.py が実行されるようにしておく

2. 外部サーバに coffee-upd.cgi と coffee-mon.cgi を置いて、cgi-binから起動できるようにしておく

3. 必要があれば、ラズパイで wpa_check.pyも起動する。


