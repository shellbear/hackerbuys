"""Category lexicon + product-line gazetteer. Regexes are RE2 and applied to lowercased, HTML-decoded text."""

# category -> generic nouns. Deliberately broad; precision is measured, not assumed.
CATEGORIES = {
 "chairs": r"office chairs?|desk chairs?|ergonomic chairs?|gaming chairs?|task chairs?|kneeling chairs?|aeron|herman miller|steelcase|haworth|secretlab|hag capisco|capisco|embody chair|gesture chair|leap v2",
 "desks": r"standing desks?|sit[- ]stand|stand(?:ing)?[- ]up desks?|motorized desks?|desk converter|uplift desk|fully jarvis|ikea bekant|ikea idasen|treadmill desk|under[- ]desk",
 "monitors": r"monitors?|ultrawides?|4k displays?|5k displays?|studio display|pro display xdr|oled tv|lg ultrafine|dell u\d{4}|e-ink monitor|dasung|boox mira",
 "keyboards": r"keyboards?|cherry mx|kinesis (?:advantage|freestyle|keyboard|ergo|360)|ergodox|hhkb|happy hacking|das keyboard|model m\b|realforce|topre|moonlander|keychron|zsa voyager|keyboardio",
 "mice_trackpads": r"trackballs?|trackpads?|magic mouse|mx master|mx ergo|gaming mouse|vertical mouse|wireless mouse|logitech mouse|deathadder|my mouse|a mouse\b",
 "headphones": r"headphones?|earbuds?|iems?\b|headsets?|airpods?|sennheiser|hd ?(?:600|650|800)\b|wh-?1000xm\d|bose qc ?\d+|quietcomfort|beyerdynamic|audio[- ]technica|ath-m\d+|noise[- ]cancell?ing",
 "laptops": r"laptops?|thinkpads?|macbooks?|xps ?1[357]|framework laptop|chromebooks?|surface laptop|surface book|zenbook|system76",
 "phones": r"iphones?(?: ?\d+| se| pro)?|pixel ?\d+\w?|galaxy s\d+|fairphone|oneplus|nexus ?\d|my phone|android phone|smartphones?|nokia \d+|blackberry",
 "tablets_ereaders": r"kindle|kobo|remarkable(?: ?2| paper)?|ipad|e-?readers?|e-?ink tablet|boox|supernote|paperwhite",
 "audio_hifi": r"speakers?|soundbars?|turntable|dac\b|amplifiers?|sonos|klipsch|kef\b|schiit|bookshelf speakers|studio monitors|microphones?|shure sm7b?|blue yeti",
 "cameras": r"mirrorless|dslr|fujifilm|fuji x\d+|sony a7|canon eos|leica|gopro|webcams?|brio\b|ricoh gr|camera lens",
 "networking": r"routers?|ubiquiti|unifi|mikrotik|edgerouter|access points?|openwrt|pfsense box|fritz!?box|mesh wifi|synology|qnap|\bnas\b|ethernet switch",
 "pc_components": r"gpus?\b|graphics card|rtx ?\d{3,4}|gtx ?\d{3,4}|ryzen|threadripper|ssds?\b|samsung 9\d0|nvme|mechanical hard|noctua|mac (?:mini|studio|pro)\b|nuc\b|mini pc|beelink",
 "sbc_maker": r"raspberry pi|arduino|esp32|esp8266|3d printers?|prusa|bambu|ender 3|soldering iron|oscilloscope|rigol|pinecil|flipper zero|multimeter",
 "gaming": r"steam deck|nintendo switch|playstation|ps[345]\b|xbox|game boy|analogue pocket|valve index|quest ?[23]|oculus|vision pro",
 "wearables_watches": r"apple watch|garmin|fitbit|oura|whoop|casio|seiko|g-?shock|pebble watch|smart ?watch|mechanical watch|citizen eco|tissot|rolex",
 "kitchen_coffee": r"espresso machine|aeropress|burr grinder|moka pot|baratza|breville|rancilio|gaggia|french press|instant pot|air fryer|cast iron|lodge skillet|chef'?s knife|wusthof|victorinox|vitamix|sous vide|anova (?:sous|precision|nano|cooker)|rice cooker|zojirushi|kitchenaid|dutch oven|le creuset|carbon steel pan",
 "home_appliances": r"robot vacuum|roomba|roborock|dyson|miele|vacuum cleaner|dishwasher|washing machine|bidet|toto washlet|air purifier|coway|heat pump|nest thermostat|ecobee|dehumidifier|induction (?:stove|cooktop|range)|hue bulbs?|philips hue",
 "bed_sleep": r"mattress(?:es)?|casper|tempur|sleep mask|eight sleep|weighted blanket|duvet|memory foam|earplugs|white noise machine|loop earplugs",
 "bags_luggage": r"backpacks?|tom bihn|peak design|osprey|patagonia black hole|carry-?on|rimowa|briggs & riley|duffel|messenger bag|aer travel|luggage",
 "clothing_shoes": r"(?:hiking|leather|work|winter|chelsea|rain|ski) boots?\b|red wing|blundstone|allen edmonds|merino|darn tough|smartwool|uniqlo|arc'?teryx|barefoot shoes|vivobarefoot|birkenstock|running shoes|goodyear welt|levi'?s 501|selvedge|allbirds|rain jacket",
 "tools_edc": r"leatherman|multi-?tool|victorinox|my swiss army|flashlight|anker|power bank|usb-?c charger|milwaukee|dewalt|makita|festool|ryobi|cordless drill|torque wrench|pocket knife|benchmade|spyderco|wera|knipex",
 "pens_paper": r"fountain pens?|lamy|pilot g-?2|pilot metropolitan|rotring|leuchtturm|moleskine|field notes|rhodia|hobonichi|mechanical pencils?|blackwing|hipster pda",
 "bikes_mobility": r"e-?bikes?|brompton|road bike|electric scooter|cargo bike|commuter bike|gravel bike|onewheel|vanmoof",
 "fitness": r"rowing machine|concept2|peloton|kettlebells?|adjustable dumbbells?|pull-?up bar|power rack|squat rack|bowflex|treadmill|yoga mat|massage gun|theragun",
 "lighting_desk": r"benq screenbar|monitor light|desk lamps?|monitor arm|ergotron|cri lights?|dyson lamp|sad lamp|light therapy lamp|cable management",
}

OWN = r"\b(?:i|we)(?:'ve|'d| have| had)? (?:just |recently |finally |also |actually |always |personally |now )?(?:bought|buy|purchased|ordered|got|own|owned|use|used|using|love|loved|switched to|upgraded to|replaced|went with|ended up with|picked up|swear by|have been using|been using|tried|returned|regret)\b"
REC = r"\b(?:highly |strongly |heartily |would |can |i |definitely )recommend|\brecommend(?:ation|ed)?\b|\bswear by\b|\bbest (?:\w+ ){0,3}(?:i(?:'ve| have)? (?:ever )?(?:bought|owned|used|had|purchased))|\bworth (?:every|the (?:money|price|investment))|\bbest purchase|\bbuy it for life|\bbifl\b|\bgame[- ]?changer|\blife[- ]?chang|\bcan'?t live without|\bstill going strong|\bbought (?:a|an|the|my|one)\b|\blasted (?:me )?\d+ years"
TENURE = r"\b(?:for|had|owned|using)(?: it| them| mine| one| this)?(?: for)?(?: over| about| almost| nearly| like| around)? (?:\d+|two|three|four|five|six|seven|eight|nine|ten|fifteen|twenty|several|many) (?:\+ )?(?:years?|decades?)\b"
NEG = r"\b(?:avoid|regret|returned it|sent (?:it|them) back|piece of (?:junk|crap|shit)|garbage|broke (?:after|within)|died (?:after|within)|stopped working|fell apart|waste of money|terrible|never (?:again|buy)|disappointed|overpriced|don'?t buy|do not buy|worst)\b"
RETAIL = r"amazon\.[a-z.]+/(?:[^ ]*/)?(?:dp|gp/product)/[a-z0-9]{10}|bhphotovideo\.com|rtings\.com|thewirecutter\.com|nytimes\.com/wirecutter|ifixit\.com|aliexpress\.com/item|bestbuy\.com|newegg\.com|ikea\.com|kickstarter\.com/projects"
# First-person possession directly of a category noun, e.g. "my aeron", "my old thinkpad". Added at SQL build time.
THREAD = r"(?i)(ask hn|tell hn|poll).*(recommend|best|favou?rite|what .*(use|bought|buy|setup|desk|gear|hardware)|worth|gift|buy it for life|bifl|chair|desk|monitor|keyboard|headphone|laptop|mattress|setup|gear|purchase|bought)"
