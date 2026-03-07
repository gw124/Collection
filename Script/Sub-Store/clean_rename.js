function operator(proxies) {
    // === 获取 URL 参数中的自定义前缀 ===
    // 例如传入 #name=GLaDOS｜，这里就会获取到 "GLaDOS｜"
    const args = typeof $arguments !== 'undefined' ? $arguments : {};
    let prefix = args.name ? decodeURIComponent(args.name) : "";

    const TAG_SEP = "｜";   // 标签之间的分隔符 (全角)

    // === 1. 标签提取与统称规则 ===
    const tagDict = {
        "Zx": "专线", "专线": "专线", 
        "IPLC": "IPLC", "IEPL": "IEPL", 
        "Fam": "家宽", "家宽": "家宽", 
        "直连": "直连", "Direct": "直连", 
        "中继": "中转", "Relay": "中转", "Transit": "中转", "中转": "中转", 
        "动态": "动态", 
        "IPV6": "IPv6", "IPv6": "IPv6",
        "流媒体": "流媒体", "Netflix": "Netflix", "Disney": "Disney", 
        "chatGPT": "OpenAI", "OpenAI": "OpenAI",
        "BGP": "BGP", "CN2": "CN2", "GIA": "GIA", "CMI": "CMI", "CMIN": "CMIN", 
        "AIG": "AIG", "PCCW": "PCCW", "HKT": "HKT", "EIP": "EIP" 
    };

    // 按关键词长度从长到短排序，防止短词误匹配长词
    const sortedTagKeys = Object.keys(tagDict).sort((a, b) => b.length - a.length);

    // === 2. 地区识别规则 ===
    const countryMap = [
        { keys: /香港|港|HK|Hong/i, flag: '🇭🇰', name: '香港' },
        { keys: /台湾|台|TW|Tai|新北/i, flag: '🇨🇳', name: '台湾' }, // 强制显示中国国旗
        { keys: /澳门|澳|MO|Macau|Macao/i, flag: '🇲🇴', name: '澳门' },
        { keys: /日本|日|JP|Japan|Tokyo|Osaka/i, flag: '🇯🇵', name: '日本' },
        { keys: /韩国|韩|KR|Korea|Seoul|春川/i, flag: '🇰🇷', name: '韩国' },
        { keys: /新加坡|新|SG|Singapore|狮城/i, flag: '🇸🇬', name: '新加坡' },
        { keys: /美国|美|US|America|United States|洛杉矶|硅谷|西雅图/i, flag: '🇺🇸', name: '美国' },
        { keys: /英国|英|GB|UK|London/i, flag: '🇬🇧', name: '英国' },
        { keys: /德国|德|DE|Germany|法兰克福/i, flag: '🇩🇪', name: '德国' },
        { keys: /加拿大|加|CA|Canada/i, flag: '🇨🇦', name: '加拿大' },
        { keys: /澳洲|澳大利亚|澳|AU|Australia|悉尼/i, flag: '🇦🇺', name: '澳洲' },
        { keys: /法国|法|FR|France|巴黎/i, flag: '🇫🇷', name: '法国' },
        { keys: /俄罗斯|俄|RU|Russia|莫斯科/i, flag: '🇷🇺', name: '俄罗斯' },
        { keys: /印度|印|IN|India|孟买/i, flag: '🇮🇳', name: '印度' },
        { keys: /泰国|泰|TH|Thailand|曼谷/i, flag: '🇹🇭', name: '泰国' },
        { keys: /马来西亚|马|MY|Malaysia/i, flag: '🇲🇾', name: '马来西亚' },
        { keys: /土耳其|土|TR|Turkey/i, flag: '🇹🇷', name: '土耳其' },
        { keys: /越南|越|VN|Vietnam/i, flag: '🇻🇳', name: '越南' },
        { keys: /印尼|ID|Indonesia/i, flag: '🇮🇩', name: '印尼' },
        { keys: /菲律宾|菲|PH|Philippines/i, flag: '🇵🇭', name: '菲律宾' },
        { keys: /中国|中|CN|China|北京|上海|广州|深圳/i, flag: '🇨🇳', name: '中国' }
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
                // 匹配后抹除该关键词，避免重复识别
                tempName = tempName.replace(regex, "");
            }
        });

        // --- C. 倍率提取 ---
        let multiplier = "";
        const blMatch = oldName.match(/((倍率|X|x|×)\D?((\d{1,3}\.)?\d+)\D?)|((\d{1,3}\.)?\d+)(倍|X|x|×)/i);
        if (blMatch) {
            const rev = blMatch[0].match(/(\d[\d.]*)/)[0];
            if (rev !== "1" && rev !== "1.0") {
                multiplier = rev + "x"; 
            }
        }

        if (!grouped[cName]) {
            grouped[cName] = { flag: cFlag, items: [] };
        }
        grouped[cName].items.push({ proxy: p, tags: tags, multi: multiplier, oldName: oldName });
    });

    let result = [];
    
    // --- D. 地区排序 ---
    const sortOrder = ['香港', '台湾', '澳门', '日本', '韩国', '新加坡', '美国', '英国', '德国', '澳洲', '法国', '俄罗斯', '印度', '泰国', '马来西亚', '土耳其', '越南', '印尼', '菲律宾', '中国', '未知'];
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
            
            // 基础名字拼接：只负责国旗、国家和序号
            let coreName = `${cFlag} ${region} ${seq}`;
            
            // 加上用户通过参数传进来的 prefix (如：GLaDOS｜🇨🇳 台湾 01)
            let newName = prefix + coreName;
            
            // 追加标签
            if (item.tags.length > 0) {
                newName += ` [${item.tags.join(TAG_SEP)}]`;
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
