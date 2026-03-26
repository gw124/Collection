function operator(proxies) {
    // === 获取 URL 参数中的自定义前缀 ===
    const args = typeof $arguments !== 'undefined' ? $arguments : {};
    let prefix = args.name ? decodeURIComponent(args.name) : "";

    const TAG_SEP = "｜";   // 标签之间的分隔符 (全角)

    // 🚨 === 1. 强力垃圾节点过滤规则 (黑名单) ===
    proxies = proxies.filter(p => {
        let name = p.name || "";
        let server = p.server || "";
        
        // 过滤假 IP
        if (/^(0\.0\.0\.0|127\.0\.0\.1|1\.1\.1\.1|8\.8\.8\.8)$/.test(server)) return false;
        
        // 匹配各种烦人的广告和提示节点
        const trashRegex = /(官网|网址|获取|订阅|到期|过期|剩余|套餐|联系|邮箱|客服|通知|打不开|浏览器|最新客户端|下载新客户端|公告|发布|用不了|教程|导航|重置|续费|资源服|教学服|emby|porn|http:\/\/|https:\/\/|过滤掉)/i;
        if (trashRegex.test(name)) return false;
        
        return true; 
    });

    // === 2. 标签提取与统称规则 ===
    const tagDict = {
        "Zx": "专线", "专线": "专线", 
        "IPLC": "IPLC", "IEPL": "IEPL", 
        "Fam": "家宽", "家宽": "家宽", 
        "直连": "直连", "Direct": "直连", 
        "中继": "中转", "Relay": "中转", "Transit": "中转", "中转": "中转", 
        "深移": "中转", "广移": "中转", "沪日": "中转", "杭日": "中转",
        "动态": "动态", 
        "IPV6": "IPv6", "IPv6": "IPv6",
        "流媒体": "流媒体", "Netflix": "Netflix", "Disney": "Disney", 
        "chatGPT": "OpenAI", "OpenAI": "OpenAI",
        "BGP": "BGP", "CN2": "CN2", "GIA": "GIA", "CMI": "CMI", "CMIN": "CMIN", 
        "AIG": "AIG", "PCCW": "PCCW", "HKT": "HKT", "EIP": "EIP" 
    };
    const sortedTagKeys = Object.keys(tagDict).sort((a, b) => b.length - a.length);

    // === 3. 地区识别规则 (💡 完美融合了 159 个国家/地区) ===
    const countryMap = [
        { keys: /香港|港|\bHK\b|Hong\s*Kong/i, flag: '🇭🇰', name: '香港' },
        { keys: /澳门|澳|\bMO\b|Macau|Macao/i, flag: '🇲🇴', name: '澳门' },
        { keys: /台湾|台|\bTW\b|Taiwan|Tai\s*wan|新北/i, flag: '🇨🇳', name: '台湾' }, 
        { keys: /日本|日|\bJP\b|Japan|Tokyo|Osaka/i, flag: '🇯🇵', name: '日本' },
        { keys: /韩国|韩|\bKR\b|Korea|Seoul|春川/i, flag: '🇰🇷', name: '韩国' },
        { keys: /新加坡|新|\bSG\b|Singapore|狮城/i, flag: '🇸🇬', name: '新加坡' },
        { keys: /美国|美|\bUS\b|\bUSA\b|United\s*States|America|洛杉矶|硅谷|西雅图/i, flag: '🇺🇸', name: '美国' },
        { keys: /英国|英|\bGB\b|\bUK\b|United\s*Kingdom|London|England/i, flag: '🇬🇧', name: '英国' },
        { keys: /法国|法|\bFR\b|France|巴黎/i, flag: '🇫🇷', name: '法国' },
        { keys: /德国|德|\bDE\b|Germany|法兰克福/i, flag: '🇩🇪', name: '德国' },
        { keys: /澳大利亚|澳洲|澳|\bAU\b|Australia|悉尼/i, flag: '🇦🇺', name: '澳大利亚' },
        { keys: /阿联酋|迪拜|\bAE\b|Dubai|UAE/i, flag: '🇦🇪', name: '阿联酋' },
        { keys: /阿富汗|\bAF\b|Afghanistan/i, flag: '🇦🇫', name: '阿富汗' },
        { keys: /阿尔巴尼亚|\bAL\b|Albania/i, flag: '🇦🇱', name: '阿尔巴尼亚' },
        { keys: /阿尔及利亚|\bDZ\b|Algeria/i, flag: '🇩🇿', name: '阿尔及利亚' },
        { keys: /安哥拉|\bAO\b|Angola/i, flag: '🇦🇴', name: '安哥拉' },
        { keys: /阿根廷|\bAR\b|Argentina/i, flag: '🇦🇷', name: '阿根廷' },
        { keys: /亚美尼亚|\bAM\b|Armenia/i, flag: '🇦🇲', name: '亚美尼亚' },
        { keys: /奥地利|\bAT\b|Austria/i, flag: '🇦🇹', name: '奥地利' },
        { keys: /阿塞拜疆|\bAZ\b|Azerbaijan/i, flag: '🇦🇿', name: '阿塞拜疆' },
        { keys: /巴林|\bBH\b|Bahrain/i, flag: '🇧🇭', name: '巴林' },
        { keys: /孟加拉国|孟加拉|\bBD\b|Bangladesh/i, flag: '🇧🇩', name: '孟加拉国' },
        { keys: /白俄罗斯|\bBY\b|Belarus/i, flag: '🇧🇾', name: '白俄罗斯' },
        { keys: /比利时|\bBE\b|Belgium/i, flag: '🇧🇪', name: '比利时' },
        { keys: /伯利兹|\bBZ\b|Belize/i, flag: '🇧🇿', name: '伯利兹' },
        { keys: /贝宁|\bBJ\b|Benin/i, flag: '🇧🇯', name: '贝宁' },
        { keys: /不丹|\bBT\b|Bhutan/i, flag: '🇧🇹', name: '不丹' },
        { keys: /玻利维亚|\bBO\b|Bolivia/i, flag: '🇧🇴', name: '玻利维亚' },
        { keys: /波斯尼亚和黑塞哥维那|波黑|\bBA\b|Bosnia/i, flag: '🇧🇦', name: '波斯尼亚和黑塞哥维那' },
        { keys: /博茨瓦纳|\bBW\b|Botswana/i, flag: '🇧🇼', name: '博茨瓦纳' },
        { keys: /巴西|\bBR\b|Brazil/i, flag: '🇧🇷', name: '巴西' },
        { keys: /英属维京群岛|\bVG\b|British\s*Virgin/i, flag: '🇻🇬', name: '英属维京群岛' },
        { keys: /文莱|\bBN\b|Brunei/i, flag: '🇧🇳', name: '文莱' },
        { keys: /保加利亚|\bBG\b|Bulgaria/i, flag: '🇧🇬', name: '保加利亚' },
        { keys: /布基纳法索|\bBF\b|Burkina/i, flag: '🇧🇫', name: '布基纳法索' },
        { keys: /布隆迪|\bBI\b|Burundi/i, flag: '🇧🇮', name: '布隆迪' },
        { keys: /柬埔寨|\bKH\b|Cambodia/i, flag: '🇰🇭', name: '柬埔寨' },
        { keys: /喀麦隆|\bCM\b|Cameroon/i, flag: '🇨🇲', name: '喀麦隆' },
        { keys: /加拿大|加|\bCA\b|Canada/i, flag: '🇨🇦', name: '加拿大' },
        { keys: /佛得角|\bCV\b|CapeVerde/i, flag: '🇨🇻', name: '佛得角' },
        { keys: /开曼群岛|\bKY\b|CaymanIslands/i, flag: '🇰🇾', name: '开曼群岛' },
        { keys: /中非共和国|\bCF\b|Central\s*African/i, flag: '🇨🇫', name: '中非共和国' },
        { keys: /乍得|\bTD\b|Chad/i, flag: '🇹🇩', name: '乍得' },
        { keys: /智利|\bCL\b|Chile/i, flag: '🇨🇱', name: '智利' },
        { keys: /哥伦比亚|\bCO\b|Colombia/i, flag: '🇨🇴', name: '哥伦比亚' },
        { keys: /科摩罗|\bKM\b|Comoros/i, flag: '🇰🇲', name: '科摩罗' },
        { keys: /刚果\(布\)|\bCG\b|Congo-Brazzaville/i, flag: '🇨🇬', name: '刚果(布)' },
        { keys: /刚果\(金\)|\bCD\b|Congo-Kinshasa/i, flag: '🇨🇩', name: '刚果(金)' },
        { keys: /哥斯达黎加|\bCR\b|CostaRica/i, flag: '🇨🇷', name: '哥斯达黎加' },
        { keys: /克罗地亚|\bHR\b|Croatia/i, flag: '🇭🇷', name: '克罗地亚' },
        { keys: /塞浦路斯|\bCY\b|Cyprus/i, flag: '🇨🇾', name: '塞浦路斯' },
        { keys: /捷克|\bCZ\b|Czech\s*Republic/i, flag: '🇨🇿', name: '捷克' },
        { keys: /丹麦|\bDK\b|Denmark/i, flag: '🇩🇰', name: '丹麦' },
        { keys: /吉布提|\bDJ\b|Djibouti/i, flag: '🇩🇯', name: '吉布提' },
        { keys: /多米尼加共和国|\bDO\b|Dominican\s*Republic/i, flag: '🇩🇴', name: '多米尼加共和国' },
        { keys: /厄瓜多尔|\bEC\b|Ecuador/i, flag: '🇪🇨', name: '厄瓜多尔' },
        { keys: /埃及|\bEG\b|Egypt/i, flag: '🇪🇬', name: '埃及' },
        { keys: /萨尔瓦多|\bSV\b|EISalvador/i, flag: '🇸🇻', name: '萨尔瓦多' },
        { keys: /赤道几内亚|\bGQ\b|Equatorial\s*Guinea/i, flag: '🇬🇶', name: '赤道几内亚' },
        { keys: /厄立特里亚|\bER\b|Eritrea/i, flag: '🇪🇷', name: '厄立特里亚' },
        { keys: /爱沙尼亚|\bEE\b|Estonia/i, flag: '🇪🇪', name: '爱沙尼亚' },
        { keys: /埃塞俄比亚|\bET\b|Ethiopia/i, flag: '🇪🇹', name: '埃塞俄比亚' },
        { keys: /斐济|\bFJ\b|Fiji/i, flag: '🇫🇯', name: '斐济' },
        { keys: /芬兰|\bFI\b|Finland/i, flag: '🇫🇮', name: '芬兰' },
        { keys: /加蓬|\bGA\b|Gabon/i, flag: '🇬🇦', name: '加蓬' },
        { keys: /冈比亚|\bGM\b|Gambia/i, flag: '🇬🇲', name: '冈比亚' },
        { keys: /格鲁吉亚|\bGE\b|Georgia/i, flag: '🇬🇪', name: '格鲁吉亚' },
        { keys: /加纳|\bGH\b|Ghana/i, flag: '🇬🇭', name: '加纳' },
        { keys: /希腊|\bGR\b|Greece/i, flag: '🇬🇷', name: '希腊' },
        { keys: /格陵兰|\bGL\b|Greenland/i, flag: '🇬🇱', name: '格陵兰' },
        { keys: /危地马拉|\bGT\b|Guatemala/i, flag: '🇬🇹', name: '危地马拉' },
        { keys: /几内亚|\bGN\b|Guinea/i, flag: '🇬🇳', name: '几内亚' },
        { keys: /圭亚那|\bGY\b|Guyana/i, flag: '🇬🇾', name: '圭亚那' },
        { keys: /海地|\bHT\b|Haiti/i, flag: '🇭🇹', name: '海地' },
        { keys: /洪都拉斯|\bHN\b|Honduras/i, flag: '🇭🇳', name: '洪都拉斯' },
        { keys: /匈牙利|\bHU\b|Hungary/i, flag: '🇭🇺', name: '匈牙利' },
        { keys: /冰岛|\bIS\b|Iceland/i, flag: '🇮🇸', name: '冰岛' },
        { keys: /印度|印|\bIN\b|India|孟买/i, flag: '🇮🇳', name: '印度' },
        { keys: /印尼|印度尼西亚|\bID\b|Indonesia|雅加达/i, flag: '🇮🇩', name: '印尼' },
        { keys: /伊朗|\bIR\b|Iran/i, flag: '🇮🇷', name: '伊朗' },
        { keys: /伊拉克|\bIQ\b|Iraq/i, flag: '🇮🇶', name: '伊拉克' },
        { keys: /爱尔兰|\bIE\b|Ireland/i, flag: '🇮🇪', name: '爱尔兰' },
        { keys: /马恩岛|\bIM\b|Isle\s*of\s*Man/i, flag: '🇮🇲', name: '马恩岛' },
        { keys: /以色列|\bIL\b|Israel/i, flag: '🇮🇱', name: '以色列' },
        { keys: /意大利|\bIT\b|Italy/i, flag: '🇮🇹', name: '意大利' },
        { keys: /科特迪瓦|\bCI\b|Ivory\s*Coast/i, flag: '🇨🇮', name: '科特迪瓦' },
        { keys: /牙买加|\bJM\b|Jamaica/i, flag: '🇯🇲', name: '牙买加' },
        { keys: /约旦|\bJO\b|Jordan/i, flag: '🇯🇴', name: '约旦' },
        { keys: /哈萨克斯坦|哈萨克|\bKZ\b|Kazakstan/i, flag: '🇰🇿', name: '哈萨克斯坦' },
        { keys: /肯尼亚|\bKE\b|Kenya/i, flag: '🇰🇪', name: '肯尼亚' },
        { keys: /科威特|\bKW\b|Kuwait/i, flag: '🇰🇼', name: '科威特' },
        { keys: /吉尔吉斯斯坦|\bKG\b|Kyrgyzstan/i, flag: '🇰🇬', name: '吉尔吉斯斯坦' },
        { keys: /老挝|\bLA\b|Laos/i, flag: '🇱🇦', name: '老挝' },
        { keys: /拉脱维亚|\bLV\b|Latvia/i, flag: '🇱🇻', name: '拉脱维亚' },
        { keys: /黎巴嫩|\bLB\b|Lebanon/i, flag: '🇱🇧', name: '黎巴嫩' },
        { keys: /莱索托|\bLS\b|Lesotho/i, flag: '🇱🇸', name: '莱索托' },
        { keys: /利比里亚|\bLR\b|Liberia/i, flag: '🇱🇷', name: '利比里亚' },
        { keys: /利比亚|\bLY\b|Libya/i, flag: '🇱🇾', name: '利比亚' },
        { keys: /立陶宛|\bLT\b|Lithuania/i, flag: '🇱🇹', name: '立陶宛' },
        { keys: /卢森堡|\bLU\b|Luxembourg/i, flag: '🇱🇺', name: '卢森堡' },
        { keys: /马其顿|\bMK\b|Macedonia/i, flag: '🇲🇰', name: '马其顿' },
        { keys: /马达加斯加|\bMG\b|Madagascar/i, flag: '🇲🇬', name: '马达加斯加' },
        { keys: /马拉维|\bMW\b|Malawi/i, flag: '🇲🇼', name: '马拉维' },
        { keys: /马来西亚|马来|马|\bMY\b|Malaysia/i, flag: '🇲🇾', name: '马来西亚' },
        { keys: /马尔代夫|\bMV\b|Maldives/i, flag: '🇲🇻', name: '马尔代夫' },
        { keys: /马里|\bML\b|Mali/i, flag: '🇲🇱', name: '马里' },
        { keys: /马耳他|\bMT\b|Malta/i, flag: '🇲🇹', name: '马耳他' },
        { keys: /毛利塔尼亚|\bMR\b|Mauritania/i, flag: '🇲🇷', name: '毛利塔尼亚' },
        { keys: /毛里求斯|\bMU\b|Mauritius/i, flag: '🇲🇺', name: '毛里求斯' },
        { keys: /墨西哥|\bMX\b|Mexico/i, flag: '🇲🇽', name: '墨西哥' },
        { keys: /摩尔多瓦|\bMD\b|Moldova/i, flag: '🇲🇩', name: '摩尔多瓦' },
        { keys: /摩纳哥|\bMC\b|Monaco/i, flag: '🇲🇨', name: '摩纳哥' },
        { keys: /蒙古|\bMN\b|Mongolia/i, flag: '🇲🇳', name: '蒙古' },
        { keys: /黑山共和国|\bME\b|Montenegro/i, flag: '🇲🇪', name: '黑山共和国' },
        { keys: /摩洛哥|\bMA\b|Morocco/i, flag: '🇲🇦', name: '摩洛哥' },
        { keys: /莫桑比克|\bMZ\b|Mozambique/i, flag: '🇲🇿', name: '莫桑比克' },
        { keys: /缅甸|\bMM\b|Myanmar/i, flag: '🇲🇲', name: '缅甸' },
        { keys: /纳米比亚|\bNA\b|Namibia/i, flag: '🇳🇦', name: '纳米比亚' },
        { keys: /尼泊尔|\bNP\b|Nepal/i, flag: '🇳🇵', name: '尼泊尔' },
        { keys: /荷兰|\bNL\b|Netherlands|阿姆斯特丹/i, flag: '🇳🇱', name: '荷兰' },
        { keys: /新西兰|\bNZ\b|New\s*Zealand/i, flag: '🇳🇿', name: '新西兰' },
        { keys: /尼加拉瓜|\bNI\b|Nicaragua/i, flag: '🇳🇮', name: '尼加拉瓜' },
        { keys: /尼日尔|\bNE\b|Niger/i, flag: '🇳🇪', name: '尼日尔' },
        { keys: /尼日利亚|\bNG\b|Nigeria/i, flag: '🇳🇬', name: '尼日利亚' },
        { keys: /朝鲜|\bKP\b|NorthKorea/i, flag: '🇰🇵', name: '朝鲜' },
        { keys: /挪威|\bNO\b|Norway/i, flag: '🇳🇴', name: '挪威' },
        { keys: /阿曼|\bOM\b|Oman/i, flag: '🇴🇲', name: '阿曼' },
        { keys: /巴基斯坦|\bPK\b|Pakistan/i, flag: '🇵🇰', name: '巴基斯坦' },
        { keys: /巴拿马|\bPA\b|Panama/i, flag: '🇵🇦', name: '巴拿马' },
        { keys: /巴拉圭|\bPY\b|Paraguay/i, flag: '🇵🇾', name: '巴拉圭' },
        { keys: /秘鲁|\bPE\b|Peru/i, flag: '🇵🇪', name: '秘鲁' },
        { keys: /菲律宾|菲|\bPH\b|Philippines/i, flag: '🇵🇭', name: '菲律宾' },
        { keys: /葡萄牙|\bPT\b|Portugal/i, flag: '🇵🇹', name: '葡萄牙' },
        { keys: /波多黎各|\bPR\b|PuertoRico/i, flag: '🇵🇷', name: '波多黎各' },
        { keys: /卡塔尔|\bQA\b|Qatar/i, flag: '🇶🇦', name: '卡塔尔' },
        { keys: /罗马尼亚|\bRO\b|Romania/i, flag: '🇷🇴', name: '罗马尼亚' },
        { keys: /俄罗斯|俄|\bRU\b|Russia|莫斯科/i, flag: '🇷🇺', name: '俄罗斯' },
        { keys: /卢旺达|\bRW\b|Rwanda/i, flag: '🇷🇼', name: '卢旺达' },
        { keys: /圣马力诺|\bSM\b|SanMarino/i, flag: '🇸🇲', name: '圣马力诺' },
        { keys: /沙特阿拉伯|沙特|\bSA\b|SaudiArabia/i, flag: '🇸🇦', name: '沙特阿拉伯' },
        { keys: /塞内加尔|\bSN\b|Senegal/i, flag: '🇸🇳', name: '塞内加尔' },
        { keys: /塞尔维亚|\bRS\b|Serbia/i, flag: '🇷🇸', name: '塞尔维亚' },
        { keys: /塞拉利昂|\bSL\b|SierraLeone/i, flag: '🇸🇱', name: '塞拉利昂' },
        { keys: /斯洛伐克|\bSK\b|Slovakia/i, flag: '🇸🇰', name: '斯洛伐克' },
        { keys: /斯洛文尼亚|\bSI\b|Slovenia/i, flag: '🇸🇮', name: '斯洛文尼亚' },
        { keys: /索马里|\bSO\b|Somalia/i, flag: '🇸🇴', name: '索马里' },
        { keys: /南非|\bZA\b|SouthAfrica/i, flag: '🇿🇦', name: '南非' },
        { keys: /西班牙|\bES\b|Spain/i, flag: '🇪🇸', name: '西班牙' },
        { keys: /斯里兰卡|\bLK\b|SriLanka/i, flag: '🇱🇰', name: '斯里兰卡' },
        { keys: /苏丹|\bSD\b|Sudan/i, flag: '🇸🇩', name: '苏丹' },
        { keys: /苏里南|\bSR\b|Suriname/i, flag: '🇸🇷', name: '苏里南' },
        { keys: /斯威士兰|\bSZ\b|Swaziland/i, flag: '🇸🇿', name: '斯威士兰' },
        { keys: /瑞典|\bSE\b|Sweden/i, flag: '🇸🇪', name: '瑞典' },
        { keys: /瑞士|\bCH\b|Switzerland/i, flag: '🇨🇭', name: '瑞士' },
        { keys: /叙利亚|\bSY\b|Syria/i, flag: '🇸🇾', name: '叙利亚' },
        { keys: /塔吉克斯坦|\bTJ\b|Tajikstan/i, flag: '🇹🇯', name: '塔吉克斯坦' },
        { keys: /坦桑尼亚|\bTZ\b|Tanzania/i, flag: '🇹🇿', name: '坦桑尼亚' },
        { keys: /泰国|泰|\bTH\b|Thailand|曼谷/i, flag: '🇹🇭', name: '泰国' },
        { keys: /多哥|\bTG\b|Togo/i, flag: '🇹🇬', name: '多哥' },
        { keys: /汤加|\bTO\b|Tonga/i, flag: '🇹🇴', name: '汤加' },
        { keys: /特立尼达和多巴哥|\bTT\b|TrinidadandTobago/i, flag: '🇹🇹', name: '特立尼达和多巴哥' },
        { keys: /突尼斯|\bTN\b|Tunisia/i, flag: '🇹🇳', name: '突尼斯' },
        { keys: /土耳其|土|\bTR\b|Turkey|伊斯坦布尔/i, flag: '🇹🇷', name: '土耳其' },
        { keys: /土库曼斯坦|\bTM\b|Turkmenistan/i, flag: '🇹🇲', name: '土库曼斯坦' },
        { keys: /美属维尔京群岛|\bVI\b|U\.S\.Virgin/i, flag: '🇻🇮', name: '美属维尔京群岛' },
        { keys: /乌干达|\bUG\b|Uganda/i, flag: '🇺🇬', name: '乌干达' },
        { keys: /乌克兰|\bUA\b|Ukraine/i, flag: '🇺🇦', name: '乌克兰' },
        { keys: /乌拉圭|\bUY\b|Uruguay/i, flag: '🇺🇾', name: '乌拉圭' },
        { keys: /乌兹别克斯坦|\bUZ\b|Uzbekistan/i, flag: '🇺🇿', name: '乌兹别克斯坦' },
        { keys: /委内瑞拉|\bVE\b|Venezuela/i, flag: '🇻🇪', name: '委内瑞拉' },
        { keys: /越南|越|\bVN\b|Vietnam/i, flag: '🇻🇳', name: '越南' },
        { keys: /也门|\bYE\b|Yemen/i, flag: '🇾🇪', name: '也门' },
        { keys: /赞比亚|\bZM\b|Zambia/i, flag: '🇿🇲', name: '赞比亚' },
        { keys: /津巴布韦|\bZW\b|Zimbabwe/i, flag: '🇿🇼', name: '津巴布韦' },
        { keys: /安道尔|\bAD\b|Andorra/i, flag: '🇦🇩', name: '安道尔' },
        { keys: /留尼汪|\bRE\b|Reunion/i, flag: '🇷🇪', name: '留尼汪' },
        { keys: /波兰|\bPL\b|Poland/i, flag: '🇵🇱', name: '波兰' },
        { keys: /关岛|\bGU\b|Guam/i, flag: '🇬🇺', name: '关岛' },
        { keys: /梵蒂冈|\bVA\b|Vatican/i, flag: '🇻🇦', name: '梵蒂冈' },
        { keys: /列支敦士登|\bLI\b|Liechtensteins/i, flag: '🇱🇮', name: '列支敦士登' },
        { keys: /库拉索|\bCW\b|Curacao/i, flag: '🇨🇼', name: '库拉索' },
        { keys: /塞舌尔|\bSC\b|Seychelles/i, flag: '🇸🇨', name: '塞舌尔' },
        { keys: /南极|\bAQ\b|Antarctica/i, flag: '🇦🇶', name: '南极' },
        { keys: /直布罗陀|\bGI\b|Gibraltar/i, flag: '🇬🇮', name: '直布罗陀' },
        { keys: /古巴|\bCU\b|Cuba/i, flag: '🇨🇺', name: '古巴' },
        { keys: /法罗群岛|\bFO\b|Faroe\s*Islands/i, flag: '🇫🇴', name: '法罗群岛' },
        { keys: /奥兰群岛|\bAX\b|Ahvenanmaa/i, flag: '🇦🇽', name: '奥兰群岛' },
        { keys: /百慕达|\bBM\b|Bermuda/i, flag: '🇧🇲', name: '百慕达' },
        { keys: /东帝汶|\bTL\b|Timor-Leste/i, flag: '🇹🇱', name: '东帝汶' },
        { keys: /中国|中|\bCN\b|China|北京|上海|广州|深圳/i, flag: '🇨🇳', name: '中国' }
    ];

    let grouped = {};

    proxies.forEach(p => {
        let oldName = p.name || "";

        // --- A. 地区识别 ---
        let cFlag = '🏴';
        let cName = '未知';
        for (let c of countryMap) {
            if (c.keys.test(oldName)) {
                cFlag = c.flag;
                cName = c.name;
                break;
            }
        }

        // --- B. 标签提取 ---
        let tags = [];
        let tempName = oldName; 
        sortedTagKeys.forEach(key => {
            let regex = new RegExp(key, "i");
            if (regex.test(tempName)) {
                let formattedTag = tagDict[key];
                if (!tags.includes(formattedTag)) {
                    tags.push(formattedTag);
                }
                tempName = tempName.replace(regex, "");
            }
        });

        // --- C. 倍率提取 ---
        let multiplier = "";
        const blMatch = oldName.match(/((倍率|X|x|×)\D?((\d{1,3}\.)?\d+)\D?)|((\d{1,3}\.)?\d+)(倍|X|x|×)/i);
        if (blMatch) {
            const rev = blMatch[0].match(/(\d[\d.]*)/)[0];
            if (rev !== "1" && rev !== "1.0") {
                multiplier = "x" + rev; 
            }
        }

        if (!grouped[cName]) {
            grouped[cName] = { flag: cFlag, items: [] };
        }
        grouped[cName].items.push({ proxy: p, tags: tags, multi: multiplier, oldName: oldName });
    });

    let result = [];
    
    // --- D. 地区排序 (提取常用国家至前列，不常用的放后面) ---
    // 💡 保证排序优先级：常用 -> 列表原序 -> 未知
    const topRegions = [
        '香港', '台湾', '澳门', '日本', '韩国', '新加坡', '美国', '英国', '德国', '法国', 
        '加拿大', '澳大利亚', '俄罗斯', '印度', '泰国', '马来西亚', '土耳其', '越南', '印尼', '菲律宾'
    ];
    let sortedRegions = Object.keys(grouped).sort((a, b) => {
        let idxA = topRegions.indexOf(a);
        let idxB = topRegions.indexOf(b);
        
        // 如果都在常用列表里，按常用列表顺序排
        if (idxA !== -1 && idxB !== -1) return idxA - idxB;
        // 如果 A 在，B 不在，A 排前面
        if (idxA !== -1) return -1;
        // 如果 B 在，A 不在，B 排前面
        if (idxB !== -1) return 1;
        
        // 都不在常用列表里，按拼音/字母顺序排，未知放最后
        if (a === '未知') return 1;
        if (b === '未知') return -1;
        return a.localeCompare(b);
    });

    // --- E. 节点内排序与重命名 ---
    for (let region of sortedRegions) {
        let items = grouped[region].items;
        let cFlag = grouped[region].flag;

        // 排序规则：纯净节点在前，带标签节点在后
        items.sort((a, b) => {
            let aHasTag = a.tags.length > 0 ? 1 : 0;
            let bHasTag = b.tags.length > 0 ? 1 : 0;
            if (aHasTag !== bHasTag) return aHasTag - bHasTag;
            return a.oldName.localeCompare(b.oldName);
        });

        items.forEach((item, index) => {
            let seq = (index + 1).toString().padStart(2, '0');
            
            // 基础名字拼接
            let coreName = `${cFlag} ${region} ${seq}`;
            let newName = prefix + coreName;
            
            // 💡 追加标签，并在 [] 内侧加入空格
            if (item.tags.length > 0) {
                newName += ` [ ${item.tags.join(TAG_SEP)} ]`; 
            }
            
            // 追加倍率
            if (item.multi !== "") {
                newName += ` ${item.multi}`;
            }
            
            item.proxy.name = newName;
            result.push(item.proxy);
        });
    }

    return result;
}
