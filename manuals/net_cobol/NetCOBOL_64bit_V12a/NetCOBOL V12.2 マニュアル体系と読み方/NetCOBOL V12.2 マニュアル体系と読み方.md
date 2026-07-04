

# 表紙

B1WD-3461-03Z0(00)
2019年10月
Windows(64)
FUJITSU Software
NetCOBOL V12.2
マニュアル体系と読み方

# まえがき

まえがき
このたびは、NetCOBOLをお買い上げいただき、誠にありがとうございます。
本製品は、Windowsシステムで動作する64ビットCOBOLアプリケーションを開発運用するための製品です。
本書の目的
本製品のマニュアルの読み方とマニュアル体系について説明します。
NetCOBOLシリーズについて
NetCOBOLシリーズの最新情報については、富士通のサイトをご覧ください。
https://www.fujitsu.com/jp/software/cobol/
登録商標について
・ Microsoft、Windows、Visual Studio、Visual Basic、SQL Server、Internet Explorer、およびWindows Serverは、米国Microsoft
Corporationの米国およびその他の国における登録商標または商標です。
・ OracleとJavaは、Oracle Corporationおよびその子会社、関連会社の米国およびその他の国における登録商標です。文中の社名、商
品名等は各社の商標または登録商標である場合があります。
・ Adobe、Acrobat、およびReaderは、Adobe Systems Incorporatedの米国またはその他の国における商標または登録商標です。
・ その他の会社名および製品名は、それぞれの会社の商標または登録商標です。
製品の呼び名について
本書では、各製品を以下のように略記しています。あらかじめご了承ください。
ソフトウェア名称 略称
Microsoft(R) Windows Server(R) 2019 Datacenter
Microsoft(R) Windows Server(R) 2019 Standard
Microsoft(R) Windows Server(R) 2019 Essentials
Windows Server 2019
Microsoft(R) Windows Server(R) 2016 Datacenter
Microsoft(R) Windows Server(R) 2016 Standard
Microsoft(R) Windows Server(R) 2016 Essentials
Windows Server 2016
Microsoft(R) Windows Server(R) 2012 R2 Datacenter
Microsoft(R) Windows Server(R) 2012 R2 Standard
Microsoft(R) Windows Server(R) 2012 R2 Essentials
Microsoft(R) Windows Server(R) 2012 R2 Foundation
Windows Server 2012 R2
Microsoft(R) Windows Server(R) 2012 Datacenter
Microsoft(R) Windows Server(R) 2012 Standard
Microsoft(R) Windows Server(R) 2012 Essentials
Microsoft(R) Windows Server(R) 2012 Foundation
Windows Server 2012
Microsoft(R) Windows Server(R) 2008 R2 Datacenter
Microsoft(R) Windows Server(R) 2008 R2 Enterprise
Microsoft(R) Windows Server(R) 2008 R2 Standard
Microsoft(R) Windows Server(R) 2008 R2 Foundation
Windows Server 2008 R2
Windows(R) 10 Education
Windows(R) 10 Home
Windows 10 (x64)
- i -ソフトウェア名称 略称
Windows(R) 10 Pro
Windows(R) 10 Enterprise
Windows(R) 8.1
Windows(R) 8.1 Pro
Windows(R) 8.1 Enterprise
Windows 8.1 (x64)
Windows(R) 7 Home Premium
Windows(R) 7 Professional
Windows(R) 7 Enterprise
Windows(R) 7 Ultimate
Windows 7(x64)
Microsoft(R) Internet Explorer(R)
Windows(R) Internet Explorer(R)
Internet Explorer
Adobe(R) Acrobat(R) Reader(R) Adobe Acrobat Reader
Adobe(R) Acrobat(R) Adobe Acrobat
・ 次の製品すべてを指す場合は、「Windows」と表記しています。
－ Windows Server 2019
－ Windows Server 2016
－ Windows Server 2012 R2
－ Windows Server 2012
－ Windows Server 2008 R2
－ Windows 10(x64)
－ Windows 8.1(x64)
－ Windows 7(x64)
本書の構成
本書は以下の構成になっています。
第1章 マニュアルの読み方
本製品のマニュアルの読み方を説明しています。
第2章 マニュアル体系
本製品のマニュアルの体系を説明しています。
付録A V10以前のマニュアル体系の対比
NetCOBOL V10以前のマニュアル構成とNetCOBOL V11以降のマニュアル構成との違いを説明しています。
お願い
・ 本書を無断で他に転載しないようお願いします。
・ 本書は予告なしに変更されることがあります。
輸出管理について
本ドキュメントを輸出または第三者へ提供する場合は、お客様が居住する国および米国輸出管理関連法規等の規制をご確認のうえ、必要
な手続きをおとりください。
- ii -2019年10月
Copyright 2013-2019 FUJITSU LIMITED
- iii -

# 目 次

目　次
第1章 マニュアルの読み方.........................................................................................................................................................1
第2章 マニュアル体系................................................................................................................................................................2
付録A V10以前のマニュアル体系の対比................................................................................................................................... 6
- iv -

# 第1章 マニュアルの読み方

第1章 マニュアルの読み方
本製品の各マニュアルの読み方を説明します。
マニュアルの適用製品
本製品のマニュアルは、以下の製品に適用されます。
・ NetCOBOL Enterprise Edition 開発パッケージ (64bit)
・ NetCOBOL Standard Edition 開発パッケージ (64bit)
・ NetCOBOL Base Edition 開発パッケージ (64bit)
・ NetCOBOL Enterprise Edition サーバ運用パッケージ (64bit)
・ NetCOBOL Standard Edition サーバ運用パッケージ (64bit)
・ NetCOBOL Base Edition サーバ運用パッケージ (64bit)
・ NetCOBOL Standard Edition クライアント運用パッケージ (64bit)
・ NetCOBOL Base Edition クライアント運用パッケージ (64bit)
マニュアル名称の表記
本製品のマニュアルでは、マニュアル名称の記載において、マニュアル名の先頭の製品名を省略している場合があります。
マニュアル内に記載されたURLに関する注意事項
マニュアル内で参照先として記載されたURLは、2018年 10月時点のものです。
- 1 -

# 第2章 マニュアル体系

第2章 マニュアル体系
本製品に含まれる各プログラムの使用方法や運用の詳細などを説明した各種オンラインマニュアルを用意しています。必要とする場面に合
わせて各オンラインマニュアルをお読みください。
PDFマニュアルの参照
以下の環境で参照してください。
・ マニュアルは、Adobe Acrobat ReaderまたはAdobe Acrobatでご覧ください。
・ Adobe Acrobat ReaderおよびAdobe Acrobatは、アップデートを適用し、最新の状態にしてください。
マニュアルの全文検索
“NetCOBOLソフトウェア説明書”の“3.1 オンラインマニュアル”に記載された方法で検索してください。
参照
NetCOBOL V10以前とNetCOBOL V11では、マニュアル体系が異なります。詳細は、“付録A V10以前のマニュアル体系の対比”を参照
してください。
マニュアル体系
マニュアル名 マニュアルの概要・参照の契機
Enterprise Edition 開発パッケージ
Standard Edition 開発パッケージ
Base Edition 開発パッケージ
Enterprise Edition サーバ運用パッケージ
Standard Edition サーバ運用パッケージ
Base Edition サーバ運用パッケージ
Standard Edition クライアント運用パッケージ
Base Edition クライアント運用パッケージ
はじめに
マニュアル体系と読み方 マニュアルの読み方とマニュア
ル体系を説明しています。
○ ○ ○ ○ ○ ○ ○ ○
入門ガイド 本製品の特長と簡単な使用方
法を説明しています。
本製品が提供するサンプルプ
ログラムを説明しています。
○ ○ ○ － － － － －
リリース情報 今回のバージョン・レベルより追
加、提供停止、修正された機能
およびバージョン・レベル間の
互換に関する情報を説明して
います。
○ ○ ○ ○ ○ ○ ○ ○
アプリケーションの開発と運用
NetCOBOLユーザーズガイド NetCOBOLの機能と
NetCOBOLを利用した
○ ○ ○ ○ ○ ○ ○ ○
- 2 -マニュアル名 マニュアルの概要・参照の契機
Enterprise Edition 開発パッケージ
Standard Edition 開発パッケージ
Base Edition 開発パッケージ
Enterprise Edition サーバ運用パッケージ
Standard Edition サーバ運用パッケージ
Base Edition サーバ運用パッケージ
Standard Edition クライアント運用パッケージ
Base Edition クライアント運用パッケージ
COBOLプログラムの作成、翻
訳・実行およびデバッグの方法
を説明しています。
NetCOBOLユーザーズガイド (他社COBOL資産移行支援編
)
他社COBOLの開発資産を
NetCOBOLに移行する方法に
ついて説明しています。
○
○
○
－
－
－
－
－
NetCOBOL Studio 
ユーザーズガイド
COBOLプログラムを開発する
ための統合開発環境を説明し
ています。
○
○
○
－
－
－
－
－
NetCOBOL CBLサブルーチン
ユーザーズガイド
CBLサブルーチンの種類や使
用方法を説明しています。
○
○
○
－
－
－
－
－
NetCOBOL LEサブルーチン
ユーザーズガイド
LEサブルーチンの種類
や使用
方法を説明しています。
○
○
○
－
－
－
－
－
Jアダプタクラスジェネレータ
ユーザーズガイド
Jアダプタクラスジェネレータは
、
Java(TM)クラスを呼び出す
COBOLクラス
(アダプタクラス
)
を生成するツールです。 Jアダプタクラスジェネレータの
機能
と使用方法
を説明していま
す。
○
○
－
○
○
－
－
－
FORM ユーザーズガイド FORMは、利用者プログラムで
使用する画面
・帳票
を設計する
ために使用します。
FORMの機能と使用方法を説
明しています。
○
○
－
－
－
－
－
－
MeFt ユーザーズガイド MeFtは、利用者プログラムから
プリンタ装置に対して帳票出力
をサポートするサービスライブラ
リです。
MeFtの機能と使用方法を説明
しています。
○
○
－
○
○
－
○
－
MeFt/Web ユーザーズガイド MeFt/Webは、Webサーバ上で
動作する利用者プログラムの
ディスプレイ装置やプリンタ装
置に対する入出力を、Webブラ
ウザ上で行うことができる通信
プログラムです。
○
○
－
○
○
－
－
－
- 3 -マニュアル名 マニュアルの概要・参照の契機
Enterprise Edition 開発パッケージ
Standard Edition 開発パッケージ
Base Edition 開発パッケージ
Enterprise Edition サーバ運用パッケージ
Standard Edition サーバ運用パッケージ
Base Edition サーバ運用パッケージ
Standard Edition クライアント運用パッケージ
Base Edition クライアント運用パッケージ
MeFt/Webの機能と使用方法
を説明しています。
NetCOBOL MeFt/Web ユーザー
ズガイド（HTML変換方式編）
MeFt/Web HTML変換方式は、
画面定義体をHTMLファイル
に変換して、表示ファイルアプ
リケーションをWebブラウザで
利用可能にする機能です。
MeFt/Web HTML変換方式の
機能と使用方法を説明していま
す。
○ ○ － ○ ○ － － －
NetCOBOL Migration CJC for
INTARFRM 連携機能運用ガイド
Migration CJC for
INTARFRM 連携機能の運用
において、特に注意すべき事
項や参考となる情報などを記載
しています。
○ ○ － ○ ○ － － －
SIMPLIA/COBOL支援キット ユーザーズガイド ○ － － － － － － －
SIMPLIA/TF-LINDA 
ユーザーズガイド
SIMPLIA/TF-LINDAは、アプ
リケーションプログラムを作成す
ることなく、テストデータを汎用
的に作成できるテストデータ作
成支援ツールです。
SIMPLIA/TF-LINDAの機能と
使用方法を説明しています。
○ － － － － － － －
SIMPLIA/TF-MDPORT 
ユーザーズガイド
SIMPLIA/TF-MDPORTは、
異なるプラットフォーム間での
データファイル形式の変換や
文字コードの変換などシームレ
スなデータの流通を実現する
資産流用支援ツールです。
SIMPLIA/TF-MDPORTの機
能と使用方法を説明しています。
○ － － － － － － －
SIMPLIA/MF￾STEPCOUNTER 
ユーザーズガイド
SIMPLIA/MF￾STEPCOUNTERは、プログラ
ム開発ステップを詳細に計測
するツールです。
○ － － － － － － －
- 4 -マニュアル名 マニュアルの概要・参照の契機
Enterprise Edition 開発パッケージ
Standard Edition 開発パッケージ
Base Edition 開発パッケージ
Enterprise Edition サーバ運用パッケージ
Standard Edition サーバ運用パッケージ
Base Edition サーバ運用パッケージ
Standard Edition クライアント運用パッケージ
Base Edition クライアント運用パッケージ
SIMPLIA/MF￾STEPCOUNTERの機能と使
用方法を説明しています。
SIMPLIA/TF-EXCOUNTER 
ユーザーズガイド
SIMPLIA/TF-EXCOUNTER
は、NetCOBOLが出力する
COUNT情報を利用して、テス
ト量の把握・テスト漏れの防止・
テストの効率化を支援するツー
ルです。
SIMPLIA/TF-EXCOUNTER
の機能と使用方法を説明して
います。
○ － － － － － － －
PowerSORT Server(64bit)ユー
ザーズガイド
PowerSORTはビジネス分野向
けの高性能なソート・マージプ
ログラムです。
PowerSORTの機能と使用方法
を説明しています。
○ － － ○ － － － －
リファレンス
COBOL文法書 FUJITSU NetCOBOL/
FUJITSU COBOL97/
FUJITSU COBOL85の
COBOL(COmmon Business
Oriented Language)に従ったプ
ログラムを書くための規則を説
明します。
○ ○ ○ － － － － －
メッセージ集 以下のメッセージを説明してい
ます。
・ 翻訳時メッセージ
・ 実行時メッセージ
・ 診断機能のメッセージ
・ MeFtのメッセージ
・ MeFt/Webのメッセージ
・ Jアダプタクラスジェネレー
タのメッセージ
○ ○ ○ ○ ○ ○ ○ ○
- 5 -

# 付録A V10以前のマニュアル体系の対比

付録A V10以前のマニュアル体系の対比
NetCOBOL V10以前とNetCOBOL V11以降では、マニュアル体系が異なります。
ここでは、NetCOBOL V10以前のマニュアル構成をもとに、NetCOBOL V11以降のマニュアル構成との違いについて説明します。
NetCOBOL V10 マニュアル名 NetCOBOL V11以降 マニュアル名
NetCOBOL リリース情報 NetCOBOL リリース情報
PowerSORT リリース情報
NetCOBOL メッセージ説明書 NetCOBOL メッセージ集
MeFt メッセージ集
NetCOBOL 例題プログラム NetCOBOL 入門ガイド
COBOL文法書 COBOL文法書
NetCOBOL 使用手引書 NetCOBOL ユーザーズガイド
NetCOBOL COBOLファイルアクセスルーチン使用手引書
- NetCOBOL ユーザーズガイド(他社COBOL資産移行支援編)
(*2)
NetCOBOL Studio 使用手引書 NetCOBOL Studioユーザーズガイド
- NetCOBOL CBLサブルーチン ユーザーズガイド(*1)
- NetCOBOL LEサブルーチン ユーザーズガイド(*1)
Jアダプタクラスジェネレータ 使用手引書 Jアダプタクラスジェネレータ ユーザーズガイド
FORM 説明書 FORM ユーザーズガイド
FORM 補足説明書
MeFt ユーザーズガイド MeFt ユーザーズガイド
MeFt/Web 説明書 MeFt/Web ユーザーズガイド
- NetCOBOL MeFt/Web ユーザーズガイド（HTML変換方式編）
(*1)
NetCOBOL Migration CJC for INTARFRM 連携機能運用ガイド NetCOBOL Migration CJC for INTARFRM 連携機能運用ガイド
SIMPLIA/TF-LINDA オンラインマニュアル SIMPLIA/COBOL支援キット ユーザーズガイド
・ SIMPLIA/TF-LINDA ユーザーズガイド
・ SIMPLIA/TF-MDPORT ユーザーズガイド
・ SIMPLIA/MF-STEPCOUNTER ユーザーズガイド
・ SIMPLIA/TF-EXCOUNTER ユーザーズガイド
SIMPLIA/TF-MDPORT オンラインマニュアル
-
-
PowerSORT ユーザーズガイド PowerSORT Server (64bit) ユーザーズガイド
*1：V12.0から提供しているマニュアルです。
*2：V12.1から提供しているマニュアルです。
- 6 -