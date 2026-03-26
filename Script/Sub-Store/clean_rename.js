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

    // === 3. 地区识别规则 (💡 新增伊拉克、哈萨克斯坦) ===
    const countryMap = [
        { keys: /香港|港|\bHK\b|Hong\s*Kong/i, flag: '🇭🇰', name: '香港' },
        { keys: /台湾|台|\bTW\b|Tai\s*wan|新北/i, flag: '🇨🇳', name: '台湾' }, 
        { keys: /澳门|澳|\bMO\b|Macau|Macao/i, flag: '🇲🇴', name: '澳门' },
        { keys: /日本|日|\bJP\b|Japan|Tokyo|Osaka/i, flag: '🇯🇵', name: '日本' },
        { keys: /韩国|韩|\bKR\b|Korea|Seoul|春川/i, flag: '🇰🇷', name: '韩国' },
        { keys: /新加坡|新|\bSG\b|Singapore|狮城/i, flag: '🇸🇬', name: '新加坡' },
        { keys: /美国|美|\bUS\b|America|United\s*States|洛杉矶|硅谷|西雅图/i, flag: '🇺🇸', name: '美国' },
        { keys: /英国|英|\bGB\b|\bUK\b|London|England/i, flag: '🇬🇧', name: '英国' },
        { keys: /德国|德|\bDE\b|Germany|法兰克福/i, flag: '🇩🇪', name: '德国' },
        { keys: /法国|法|\bFR\b|France|巴黎/i, flag: '🇫🇷', name: '法国' },
        { keys: /加拿大|加|\bCA\b|Canada/i, flag: '🇨🇦', name: '加拿大' },
        { keys: /澳洲|澳大利亚|澳|\bAU\b|Australia|悉尼/i, flag: '🇦🇺', name: '澳洲' },
        { keys: /俄罗斯|俄|\bRU\b|Russia|莫斯科/i, flag: '🇷🇺', name: '俄罗斯' },
        { keys: /印度|印|\bIN\b|India|孟买/i, flag: '🇮🇳', name: '印度' },
        { keys: /泰国|泰|\bTH\b|Thailand|曼谷/i, flag: '🇹🇭', name: '泰国' },
        { keys: /马来西亚|马|\bMY\b|Malaysia/i, flag: '🇲🇾', name: '马来西亚' },
        { keys: /土耳其|土|\bTR\b|Turkey/i, flag: '🇹🇷', name: '土耳其' },
        { keys: /越南|越|\bVN\b|Vietnam/i, flag: '🇻🇳', name: '越南' },
        { keys: /印尼|\bID\b|Indonesia|雅加达/i, flag: '🇮🇩', name: '印尼' }, 
        { keys: /菲律宾|菲|\bPH\b|Philippines/i, flag: '🇵🇭', name: '菲律宾' },
        { keys: /巴西|\bBR\b|Brazil/i, flag: '🇧🇷', name: '巴西' },
        { keys: /阿根廷|\bAR\b|Argentina/i, flag: '🇦🇷', name: '阿根廷' },
        { keys: /希腊|\bGR\b|Greece/i, flag: '🇬🇷', name: '希腊' },
        { keys: /冰岛|\bIS\b|Iceland/i, flag: '🇮🇸', name: '冰岛' },
        { keys: /葡萄牙|\bPT\b|Portugal/i, flag: '🇵🇹', name: '葡萄牙' },
        { keys: /西班牙|\bES\b|Spain/i, flag: '🇪🇸', name: '西班牙' },
        { keys: /意大利|\bIT\b|Italy/i, flag: '🇮🇹', name: '意大利' },
        { keys: /荷兰|\bNL\b|Netherlands|阿姆斯特丹/i, flag: '🇳🇱', name: '荷兰' },
        { keys: /瑞士|\bCH\b|Switzerland/i, flag: '🇨🇭', name: '瑞士' },
        { keys: /瑞典|\bSE\b|Sweden/i, flag: '🇸🇪', name: '瑞典' },
        { keys: /芬兰|\bFI\b|Finland/i, flag: '🇫🇮', name: '芬兰' },
        { keys: /波兰|\bPL\b|Poland/i, flag: '🇵🇱', name: '波兰' },
        { keys: /南非|\bZA\b|South\s*Africa/i, flag: '🇿🇦', name: '南非' },
        { keys: /智利|\bCL\b|Chile/i, flag: '🇨🇱', name: '智利' },
        { keys: /埃及|\bEG\b|Egypt/i, flag: '🇪🇬', name: '埃及' },
        { keys: /爱尔兰|\bIE\b|Ireland/i, flag: '🇮🇪', name: '爱尔兰' },
        { keys: /阿联酋|迪拜|\bAE\b|UAE|Dubai/i, flag: '🇦🇪', name: '阿联酋' },
        { keys: /新西兰|\bNZ\b|New\s*Zealand/i, flag: '🇳🇿', name: '新西兰' },
        { keys: /墨西哥|\bMX\b|Mexico/i, flag: '🇲🇽', name: '墨西哥' },
        { keys: /哥伦比亚|\bCO\b|Colombia/i, flag: '🇨🇴', name: '哥伦比亚' },
        { keys: /柬埔寨|\bKH\b|Cambodia/i, flag: '🇰🇭', name: '柬埔寨' },
        { keys: /巴基斯坦|\bPK\b|Pakistan/i, flag: '🇵🇰', name: '巴基斯坦' },
        { keys: /以色列|\bIL\b|Israel/i, flag: '🇮🇱', name: '以色列' },
        { keys: /挪威|\bNO\b|Norway/i, flag: '🇳🇴', name: '挪威' },
        { keys: /沙特|沙特阿拉伯|\bSA\b|Saudi\s*Arabia/i, flag: '🇸🇦', name: '沙特' },
        { keys: /缅甸|\bMM\b|Myanmar/i, flag: '🇲🇲', name: '缅甸' },
        { keys: /孟加拉|\bBD\b|Bangladesh/i, flag: '🇧🇩', name: '孟加拉' },
        { keys: /秘鲁|\bPE\b|Peru/i, flag: '🇵🇪', name: '秘鲁' },
        { keys: /尼日利亚|\bNG\b|Nigeria/i, flag: '🇳🇬', name: '尼日利亚' },
        { keys: /伊拉克|\bIQ\b|Iraq/i, flag: '🇮🇶', name: '伊拉克' }, // 💡 新增
        { keys: /哈萨克斯坦|哈萨克|\bKZ\b|Kazakhstan/i, flag: '🇰🇿', name: '哈萨克斯坦' }, // 💡 新增
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
    
    // --- D. 地区排序 ---
    const sortOrder = [
        '香港', '台湾', '澳门', '日本', '韩国', '新加坡', '美国', '英国', '德国', '法国', 
        '加拿大', '澳洲', '俄罗斯', '印度', '泰国', '马来西亚', '土耳其', '越南', '印尼', '菲律宾', 
        '阿联酋', '巴西', '阿根廷', '希腊', '冰岛', '葡萄牙', '西班牙', '意大利', '荷兰', '瑞士', 
        '瑞典', '芬兰', '波兰', '南非', '智利', '埃及', '爱尔兰', '新西兰', '墨西哥', '哥伦比亚', '柬埔寨', 
        '巴基斯坦', '以色列', '挪威', '沙特', '缅甸', '孟加拉', '秘鲁', '尼日利亚', '伊拉克', '哈萨克斯坦', 
        '中国', '未知'
    ];
    let sortedRegions = Object.keys(grouped).sort((a, b) => {
        let idxA = sortOrder.indexOf(a);
        let idxB = sortOrder.indexOf(b);
        if (idxA === -1) idxA = 999;
        if (idxB === -1) idxB = 999;
        return idxA - idxB;
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
            
            // 追加标签，并在 [] 内侧加入空格
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
