var monerisCloud;
(function (monerisCloud) {
    class CloudSettings {
        constructor() {
            this.$connectionMode = "cloud";
            this.connectionIPString = "";
            this.connectionIPPort = 7784;
            this.ecrId = "";
            this.merchantId = "";
            this.configCode = "";
            
            this.requestId = "";
            this.idempotencyKey = "";
            this.transactionId = "";

            this.storeId = "";
            this.token = "";
            this.terminalId = "";
            this.txnType = "";
            this.polling = "";
            this.postbackUrl = "";
            this.cloud_inout_url = "";
            this.cloud_out_url1 = "";
            this.cloud_out_url2 = "";
        }
        CloudSettings(settings) {
            this.connectionMode = settings.connectionMode;
            this.connectionIPString = settings.connectionIPString;
            this.connectionIPPort = settings.connectionIPPort;
            this.ecrId = settings.ecrId;
            this.merchantId = settings.merchantId;
            this.configCode = settings.configCode;
            
            this.requestId = settings.requestId;
            this.idempotencyKey = settings.idempotencyKey;
            this.transactionId = settings.transactionId;

            this.storeId = settings.storeId;
            this.storeId = settings.token;
            this.company_id = settings.company_id;
            this.terminalId = settings.terminalId;
            this.txnType = settings.txnType;
            this.polling = settings.polling;
            this.postbackUrl = settings.postbackUrl;
            this.cloud_inout_url = settings.cloud_inout_url;
            this.cloud_out_url1 = settings.cloud_out_url1;
            this.cloud_out_url2 = settings.cloud_out_url2;
        }
        get $connectionMode() {
            return this.connectionMode;
        }
        set $connectionMode(value) {
            this.connectionMode = value;
        }
        get $connectionIPString() {
            return this.connectionIPString;
        }
        set $connectionIPString(value) {
            this.connectionIPString = value;
        }
        get $connectionIPPort() {
            return this.connectionIPPort;
        }
        set $connectionIPPort(value) {
            this.connectionIPPort = value;
        }
        get $ecrId() {
            return this.ecrId;
        }
        set $ecrId(value) {
            this.ecrId = value;
        }
        get $merchantId() {
            return this.merchantId;
        }
        set $merchantId(value) {
            this.merchantId = value;
        }
        get $configCode() {
            return this.configCode;
        }
        set $configCode(value) {
            this.configCode = value;
        }

        get $requestId() {
            return this.requestId;
        }
        set $requestId(value) {
            this.requestId = value;
        }       
        get $idempotencyKey() {
            return this.idempotencyKey;
        }
        set $idempotencyKey(value) {
            this.idempotencyKey = value;
        }  
        get $transactionId() {
            return this.transactionId;
        }
        set $transactionId(value) {
            this.transactionId = value;
        }  


        // -----------------
        get $storeId() {
            return this.storeId;
        }
        set $storeId(value) {
            this.storeId = value;
        }
         get $token() {
            return this.token;
        }
        set $token(value) {
            this.token = value;
        }

        get $terminalId() {
            return this.terminalId;
        }
        set $terminalId(value) {
            this.terminalId = value;
        }
 
        get $txnType() {
            return this.txnType;
        }
        set $txnType(value) {
            this.txnType = value;
        } 
        get $polling() {
            return this.polling;
        }
        set $polling(value) {
            this.polling = value;
        } 
        get $PostbackUrl() {
            return this.PostbackUrl;
        }
        set $PostbackUrl(value) {
            this.PostbackUrl = value;
        } 
        get $cloud_inout_url() {
            return this.cloud_inout_url;
        }
        set $cloud_inout_url(value) {
            this.cloud_inout_url = value;
        }
        get $cloud_out_url1() {
            return this.cloud_out_url1;
        }
        set $cloud_out_url1(value) {
            this.cloud_out_url1 = value;
        }
        get $cloud_out_url2() {
            return this.cloud_out_url2;
        }
        set $cloud_out_url2(value) {
            this.cloud_out_url2 = value;
        }
        // ------------------

    }
    monerisCloud.CloudSettings = CloudSettings;
})(monerisCloud || (monerisCloud = {}));

var monerisCloud;
(function (monerisCloud) {
    class Terminal {
        constructor(settings) {
            // if (settings.$connectionMode === 
            //     "onFixIp" &&
            //     settings.$terminalId.length === 0) {
            //     throw new Error("Terminal ID can not be empty if broadcast connection mode is used");
            // }
            this.settings = new monerisCloud.CloudSettingsImmutable(settings);
        }
        get $settings() {
            return this.settings;
        }
    }
    monerisCloud.Terminal = Terminal;
})(monerisCloud || (monerisCloud = {}));


var monerisCloud;
(function (monerisCloud) {
    class CloudSettingsImmutable {
        constructor(settings) {
            if (settings == undefined) {
                throw new Error("settings cannot be undefined or null");
            }
            this.connectionMode = settings.$connectionMode;
            this.connectionIPString = settings.$connectionIPString;
            this.connectionIPPort = settings.$connectionIPPort;
            this.ecrId = settings.$ecrId;
            this.merchantId = settings.$merchantId;
            this.configCode = settings.$configCode;
            this.requestId = settings.$requestId;
            this.idempotencyKey = settings.$idempotencyKey;
            this.transactionId = settings.$transactionId;

            this.storeId = settings.storeId;
            this.token = settings.token;
            this.company_id = settings.company_id;
            this.terminalId = settings.terminalId;
            this.txnType = settings.txnType;
            this.polling = settings.polling;
            this.postbackUrl = settings.postbackUrl;
            this.cloud_inout_url = settings.cloud_inout_url;
            this.cloud_out_url1 = settings.cloud_out_url1;
            this.cloud_out_url2 = settings.cloud_out_url2;
        }
        get $connectionMode() {
            return this.connectionMode;
        }
        get $connectionIPString() {
            return this.connectionIPString;
        }
        get $connectionIPPort() {
            return this.connectionIPPort;
        }
        get $ecrId() {
            return this.ecrId;
        }
        get $merchantId() {
            return this.merchantId;
        }
        get $configCode() {
            return this.configCode;
        }
        get $terminalId() {
            return this.terminalId;
        }
        get $requestId() {
            return this.requestId;
        }
        get $idempotencyKey() {
            return this.idempotencyKey;
        }
        get $transactionId() {
            return this.transactionId;
        }
        get $storeId() {
            return this.storeId;
        }
        get $token() {
            return this.token;
        }

        get $terminalId() {
            return this.terminalId;
        }
        get $txnType() {
            return this.txnType;
        }
        get $postbackUrl() {
            return this.postbackUrl;
        }
        get $cloud_inout_url() {
            return this.cloud_inout_url;
        }
        get $cloud_out_url1() {
            return this.cloud_out_url1;
        }
        get $cloud_out_url2() {
            return this.cloud_out_url2;
        }

    }
    monerisCloud.CloudSettingsImmutable = CloudSettingsImmutable;
})(monerisCloud || (monerisCloud = {}));


var monerisCloud;
(function (monerisCloud) {
    let TimeDateFormat;
    (function (TimeDateFormat) {
        TimeDateFormat["time"] = "hh:mm:ss";
        TimeDateFormat["date"] = "dd.MM.yyyy";
        TimeDateFormat["regular"] = "dd-MM-yyyy hh:mm:ss";
    })(TimeDateFormat = monerisCloud.TimeDateFormat || (monerisCloud.TimeDateFormat = {}));
    class TimeDate {
        constructor(yearOrFormatOrDate, monthOrValue, day, hour, minute, second) {
            let date;
            switch (arguments.length) {
                case 6: {
                    this.$year = yearOrFormatOrDate;
                    this.$month = monthOrValue;
                    this.$day = day;
                    this.$hour = hour;
                    this.$minute = minute;
                    this.$second = second;
                    break;
                }
                case 2: {
                    const format = yearOrFormatOrDate;
                    const value = monthOrValue;
                    this.initWithFormatAndValue(format, value);
                    break;
                }
                case 1: {
                    date = yearOrFormatOrDate;
                    break;
                }
                case 0: {
                    date = new Date();
                    break;
                }
                default: {
                    throw new Error("Invalid argument");
                }
            }
            if (date !== undefined) {
                this.$year = date.getFullYear();
                this.$month = date.getMonth();
                this.$day = date.getDate();
                this.$hour = date.getHours();
                this.$minute = date.getMinutes();
                this.$second = date.getSeconds();
            }
        }
        get $year() {
            return this.year;
        }
        set $year(value) {
            this.year = value;
        }
        get $month() {
            return this.month;
        }
        set $month(value) {
            this.month = value;
        }
        get $day() {
            return this.day;
        }
        set $day(value) {
            this.day = value;
        }
        get $hour() {
            return this.hour;
        }
        set $hour(value) {
            this.hour = value;
        }
        get $minute() {
            return this.minute;
        }
        set $minute(value) {
            this.minute = value;
        }
        get $second() {
            return this.second;
        }
        set $second(value) {
            this.second = value;
        }
        format(format) {
            const year4 = this.$year.toString();
            const year2 = (this.$year % 100).toString();
            const month = (this.$month + 1).toString();
            const day = this.$day.toString();
            const hour = this.$hour.toString();
            const minute = this.$minute.toString();
            const second = this.$second.toString();
            const result = format
                .replace("yyyy", "0".repeat(4 - year4.length) + year4)
                .replace("yy", "0".repeat(2 - year2.length) + year2)
                .replace("MM", "0".repeat(2 - month.length) + month)
                .replace("dd", "0".repeat(2 - day.length) + day)
                .replace("HH", "0".repeat(2 - hour.length) + hour)
                .replace("mm", "0".repeat(2 - minute.length) + minute)
                .replace("ss", "0".repeat(2 - second.length) + second)
                .replace("Z", "+0000");
            return result;
        }
        initWithFormatAndValue(format, value) {
            format = format.replace(/[^a-zA-Z0-9]/g, "");
            const startIndexYear = format.indexOf("y");
            const endIndexYear = format.lastIndexOf("y");
            this.$year = parseInt(value.slice(startIndexYear, endIndexYear + 1), undefined);
            const startIndexMonth = format.indexOf("M");
            const endIndexMonth = format.lastIndexOf("M");
            this.$month = parseInt(value.slice(startIndexMonth, endIndexMonth + 1), undefined);
            const startIndexDay = format.indexOf("d");
            const endIndexDay = format.lastIndexOf("d");
            this.$day = parseInt(value.slice(startIndexDay, endIndexDay + 1), undefined);
            const startIndexHour = format.indexOf("H");
            const endIndexHour = format.lastIndexOf("H");
            this.$hour = parseInt(value.slice(startIndexHour, endIndexHour + 1), undefined);
            const startIndexMinute = format.indexOf("m");
            const endIndexMinute = format.lastIndexOf("m");
            this.$minute = parseInt(value.slice(startIndexMinute, endIndexMinute + 1), undefined);
            const startIndexSecond = format.indexOf("s");
            const endIndexSecond = format.lastIndexOf("s");
            this.$second = parseInt(value.slice(startIndexSecond, endIndexSecond + 1), undefined);
        }
        toStringRegular() {
            return this.format(TimeDateFormat.regular);
        }
        toStringReceiptDate() {
            return this.format(TimeDateFormat.date);
        }
        toStringReceiptTime() {
            return this.format(TimeDateFormat.time);
        }
    }
    monerisCloud.TimeDate = TimeDate;
})(monerisCloud || (monerisCloud = {}));
