var clovercloud;
(function (clovercloud) {
    class TerminalSettings {
        constructor() {
            this.$connectionMode = "broadcast";
            this.applicationId = "";
            this.connectionMode = "";
            this.cloverServerUrl = "";
            this.cloverConfigId = "";
            this.cloverJwtToken = "";
            this.cloverDeviceId = "";
            this.cloverDeviceName = "";
            this.cloverXPosId = "";
        }
        TerminalSettings(settings) {
            this.connectionMode = settings.connectionMode;
            this.applicationId = settings.applicationId;
            this.cloverServerUrl = settings.cloverServerUrl;
            this.cloverConfigId = settings.cloverConfigId;
            this.cloverJwtToken = settings.cloverJwtToken;
            this.cloverDeviceId = settings.cloverDeviceId;
            this.cloverDeviceName = settings.cloverDeviceName;
            this.cloverXPosId = settings.cloverXPosId;
        }
        get $applicationId() {
            return this.applicationId;
        }
        set $applicationId(value) {
            this.applicationId = value;
        }
        get $cloverServerUrl() {
            return this.cloverServerUrl;
        }
        set $cloverServerUrl(value) {
            this.cloverServerUrl = value;
        }
        get $cloverConfigId() {
            return this.cloverConfigId;
        }
        set $cloverConfigId(value) {
            this.cloverConfigId = value;
        }
        get $cloverJwtToken() {
            return this.cloverJwtToken;
        }
        set $cloverJwtToken(value) {
            this.cloverJwtToken = value;
        }
        get $cloverDeviceId() {
            return this.cloverDeviceId;
        }
        set $cloverDeviceId(value) {
            this.cloverDeviceId = value;
        }
        get $cloverDeviceName() {
            return this.cloverDeviceName;
        }
        set $cloverDeviceName(value) {
            this.cloverDeviceName = value;
        }   
        get $cloverXPosId() {
            return this.cloverXPosId;
        }
        set $cloverXPosId(value) {
            this.cloverXPosId = value;
        }  


    }
    clovercloud.TerminalSettings = TerminalSettings;
})(clovercloud || (clovercloud = {}));

var clovercloud;
(function (clovercloud) {
    class Terminal {
        constructor(settings) {
            if (settings.$connectionMode === "onFixIp"){
                if(settings.$applicationId.length === 0 || settings.$applicationId.cloverServerUrl === 0
                    || settings.$applicationId.cloverConfigId === 0 || settings.$applicationId.cloverJwtToken === 0 
                    || settings.$applicationId.cloverDeviceId === 0 
                    || settings.$applicationId.cloverDeviceName === 0 
                    || settings.$applicationId.cloverXPosId === 0 
                     ){
                        throw new Error("Please configure for clovercloud Cloud Properly. Some credentials are misising.");

                    }                
            }  
            this.settings = new clovercloud.TerminalSettingsImmutable(settings);
        }
        get $settings() {
            return this.settings;
        }
    }
    clovercloud.Terminal = Terminal;
})(clovercloud || (clovercloud = {}));


var clovercloud;
(function (clovercloud) {
    class TerminalSettingsImmutable {
        constructor(settings) {
            if (settings == undefined) {
                throw new Error("settings cannot be undefined or null");
            }
            this.applicationId = settings.$applicationId;
            this.connectionMode = settings.$connectionMode;
            this.cloverServerUrl = settings.$cloverServerUrl;
            this.cloverConfigId = settings.$cloverConfigId;
            this.cloverJwtToken = settings.$cloverJwtToken;
            this.cloverDeviceId = settings.$cloverDeviceId;
            this.cloverDeviceName = settings.$cloverDeviceName;
            this.cloverXPosId = settings.$cloverXPosId;
        }
        get $applicationId() {
            return this.applicationId;
        }
        get $connectionMode() {
            return this.connectionMode;
        }
        get $cloverServerUrl() {
            return this.cloverServerUrl;
        }
        get $cloverConfigId() {
            return this.cloverConfigId;
        }
        get $cloverJwtToken() {
            return this.cloverJwtToken;
        }
        get $cloverDeviceId() {
            return this.cloverDeviceId;
        }
        get $cloverDeviceName() {
            return this.cloverDeviceName;
        }
        get $cloverXPosId() {
            return this.cloverXPosId;
        }
    }
    clovercloud.TerminalSettingsImmutable = TerminalSettingsImmutable;
})(clovercloud || (clovercloud = {}));


var clovercloud;
(function (clovercloud) {
    let TimeDateFormat;
    (function (TimeDateFormat) {
        TimeDateFormat["time"] = "hh:mm:ss";
        TimeDateFormat["date"] = "dd.MM.yyyy";
        TimeDateFormat["regular"] = "dd-MM-yyyy hh:mm:ss";
    })(TimeDateFormat = clovercloud.TimeDateFormat || (clovercloud.TimeDateFormat = {}));
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
    clovercloud.TimeDate = TimeDate;
})(clovercloud || (clovercloud = {}));
