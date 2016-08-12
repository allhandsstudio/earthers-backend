const DAYS = [31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365];
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const START_YEAR = 2000;


var labelForTime = function(time) {
	var year_offset = Math.floor(time / 365);
	var year = String(START_YEAR + year_offset);
	var days = time - (year_offset * 365);
	var month = MONTHS[DAYS.indexOf(sanitizeTime(days))];
	return month+' '+year;
}

var sanitizeTime = function(time) {
	var base = 365 * Math.floor(time / 365);
	var remainder = time - base;
	var i = DAYS.indexOf(remainder);
	if (i == -1) {
		for (let j = 0; j < DAYS.length; j++) 
			if (remainder <= DAYS[j])
				return base + DAYS[j];
	} else 
		return time;
}

module.exports = {
	labelForTime: labelForTime,
	sanitizeTime: sanitizeTime
}