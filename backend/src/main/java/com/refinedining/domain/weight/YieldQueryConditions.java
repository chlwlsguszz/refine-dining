package com.refinedining.domain.weight;

import java.util.*;
import java.util.regex.Pattern;

/** Explicit contradictions are checked after retrieval; similarity alone never establishes equivalence. */
final class YieldQueryConditions {
    private record Term(String key, Pattern pattern) {
        Term(String key, String regex) { this(key, Pattern.compile(regex, Pattern.CASE_INSENSITIVE)); }
    }
    private static final List<Term> SPECIES = List.of(
            new Term("chicken", "닭|치킨|chicken"), new Term("beef", "소고기|쇠고기|한우|비프|beef|\\b소\\b"),
            new Term("pork", "돼지|돈육|포크|pork"), new Term("veal", "송아지|veal"),
            new Term("turkey", "칠면조|turkey"), new Term("lamb", "양고기|lamb|mutton"),
            new Term("bison", "들소|버팔로|bison"), new Term("deer", "사슴|venison|deer"),
            new Term("elk", "엘크|elk"), new Term("ostrich", "타조|ostrich"), new Term("emu", "에뮤|emu"));
    private static final List<Term> CUTS = List.of(
            new Term("thigh", "넓적|넙적|허벅지|윗다리|thigh"), new Term("drumstick", "아랫다리|북채|드럼스틱|drumstick"),
            new Term("breast", "가슴|브레스트|breast"), new Term("wing", "날개|윙|wing"),
            new Term("tenderloin", "안심|tenderloin|필레|filet|fillet"),
            new Term("loin", "등심|로인|포크찹|pork chop|\\bloin\\b"), new Term("ribeye", "꽃등심|립아이|ribeye|rib eye"),
            new Term("sirloin", "채끝|sirloin"), new Term("ribs", "갈비|\\bribs?\\b"),
            new Term("brisket", "양지|차돌|brisket"), new Term("flank", "치마살|flank"),
            new Term("round", "우둔|설도|홍두깨|round"), new Term("shoulder", "목심|목살|어깨|앞다리|shoulder|chuck"),
            new Term("ground", "다진|다짐|분쇄|패티|버거|ground|mince|patty|patties|burger"),
            new Term("liver", "\\b간\\b|liver"), new Term("heart", "심장|염통|heart"),
            new Term("kidney", "콩팥|신장|kidney"), new Term("gizzard", "모래집|닭똥집|gizzard"),
            new Term("sausage", "소시지|소세지|sausage"), new Term("bacon", "베이컨|bacon"),
            new Term("ham", "\\b햄\\b|\\bham\\b"), new Term("whole", "통닭|whole chicken|whole turkey"));
    private static final Pattern OUTSIDE_CORPUS = Pattern.compile(
            "감자|고구마|옥수수|두부|콩(?!팥)|쌀|밥|사과|버섯|연어|고등어|참치|생선|오리고기|오리|potato|corn|tofu|rice|salmon|fish|duck",
            Pattern.CASE_INSENSITIVE);
    private final String name;
    private final String method;
    private final Set<String> species;
    private final Set<String> cuts;

    YieldQueryConditions(String name, String method) {
        this.name = name;
        this.method = method == null ? "" : method.strip();
        species = detect(name, SPECIES);
        cuts = detect(name, CUTS);
        if (cuts.isEmpty() && Pattern.compile("다리|\\bleg\\b", Pattern.CASE_INSENSITIVE).matcher(name).find())
            cuts.addAll(Set.of("thigh", "drumstick", "leg"));
        if (cuts.contains("ribeye")) cuts.remove("loin");
        else if (cuts.contains("loin")) cuts.addAll(Set.of("ribeye", "sirloin"));
    }

    private static Set<String> detect(String text, List<Term> terms) {
        Set<String> found = new HashSet<>();
        terms.stream().filter(term -> term.pattern().matcher(text).find()).forEach(term -> found.add(term.key()));
        return found;
    }

    boolean outsideCorpus() { return species.isEmpty() && cuts.isEmpty() && OUTSIDE_CORPUS.matcher(name).find(); }

    int lexicalScore(MeasuredYieldCatalog.Entry entry) {
        if (!species.isEmpty() && !species.contains(entry.species())) return 0;
        int score = 0;
        String normalized = MeasuredYieldCatalog.key(name);
        if (entry.foods().stream().anyMatch(term -> term.contains(normalized) || normalized.contains(term))) score += 6;
        if (species.contains(entry.species())) score += 2;
        if (cuts.contains(entry.cut())) score += 4;
        // A species match alone is useful for a broad query, but not for an explicitly different cut.
        if (!cuts.isEmpty() && !cuts.contains(entry.cut())) return 0;
        if (!method.isBlank() && entry.methods().contains(MeasuredYieldCatalog.key(method))) score += 1;
        return score;
    }

    record Assessment(List<String> reasons, List<String> differences, boolean canEstimate, boolean exact) {}

    Assessment assess(MeasuredYieldCatalog.Entry entry) {
        List<String> reasons = new ArrayList<>(), differences = new ArrayList<>();
        boolean canEstimate = true;
        boolean exact = entry.foods().contains(MeasuredYieldCatalog.key(name));
        if (exact) reasons.add("등록된 식품명 또는 별칭과 일치합니다.");
        if (species.size() != 1) {
            differences.add("식품 종류를 하나로 확인할 수 없습니다. 닭고기·소고기·돼지고기 등을 검색어에 적어 주세요.");
            canEstimate = false;
        } else if (!species.contains(entry.species())) {
            differences.add("입력한 식품 종류와 원자료의 동물 종류가 다릅니다.");
            canEstimate = false;
        } else reasons.add("같은 동물 종류의 실측 자료입니다.");
        if (!cuts.isEmpty() && !cuts.contains(entry.cut())) {
            differences.add("입력한 부위·형태와 원자료의 부위·형태가 다릅니다.");
            canEstimate = false;
        } else if (!cuts.isEmpty()) reasons.add("입력한 부위·형태에 대응하는 자료입니다.");
        else differences.add("검색어에서 세부 부위를 확정하지 못했습니다. 자료에 적힌 부위를 확인해 주세요.");

        String compact = MeasuredYieldCatalog.key(name);
        for (String[] condition : List.of(
                new String[]{"껍질없는|껍질제거|껍질벗|skinless|withoutskin", "skin_off", "껍질 제거"},
                new String[]{"뼈없는|뼈제거|순살|boneless|withoutbone", "bone_out", "뼈 제거"})) {
            if (Pattern.compile(condition[0]).matcher(compact).find() && !entry.preparationTags().contains(condition[1])) {
                differences.add("요청한 " + condition[2] + " 조건이 원자료에서 확인되지 않습니다.");
                canEstimate = false;
            }
        }
        if (compact.matches(".*(껍질포함|skinon|withskin).*" ) && entry.preparationTags().contains("skin_off")) {
            differences.add("껍질 포함 요청과 껍질 제거 자료의 조건이 다릅니다.");
            canEstimate = false;
        }
        if (compact.matches(".*(뼈포함|bonein|withbone).*" ) && entry.preparationTags().contains("bone_out")) {
            differences.add("뼈 포함 요청과 뼈 제거 자료의 조건이 다릅니다.");
            canEstimate = false;
        }
        if (compact.matches(".*(양념|염지|소스|반죽|빵가루|두부).*" ) || OUTSIDE_CORPUS.matcher(name).find()) {
            differences.add("추가 재료나 가공 조건의 중량은 이 실험에서 확인되지 않습니다.");
            canEstimate = false;
        }
        if (compact.matches(".*(패티|버거|patty|patties|burger).*" ) && !entry.preparationTags().contains("patty")) {
            differences.add("패티 형태의 실측 자료가 아닙니다.");
            canEstimate = false;
        }
        if (!method.isBlank() && methodMatches(entry)) {
            reasons.add("입력한 조리법으로 등록된 자료입니다.");
        } else if (method.isBlank()) {
            differences.add("조리법을 입력하지 않았습니다. 자료에 적힌 조리법을 확인해 주세요.");
            exact = false;
        } else if (method.matches(".*(에어프라이|air.?fry).*" ) && entry.methodKey().equals("roast")) {
            differences.add("에어프라이어 전용 실험이 아닙니다. 오븐구이 실험을 참고하는 계산입니다.");
            exact = false;
        } else {
            differences.add("입력한 조리법과 원자료의 조리법 대응을 확인할 수 없습니다.");
            canEstimate = false;
        }
        if (entry.preparationTags().contains("skin_on") && !compact.contains("껍질") && !compact.contains("skin"))
            differences.add("이 자료는 껍질을 포함합니다. 실제 재료의 손질 상태를 확인해 주세요.");
        if (entry.source().foodLabel().contains("지방") && !compact.contains("지방") && !compact.contains("%"))
            differences.add("원자료의 지방 함량 구간을 실제 재료와 대조해 주세요.");
        if (entry.preparationTags().contains("enhanced"))
            differences.add("용액을 첨가한 원료의 실험입니다. 첨가하지 않은 원료와 조건이 다를 수 있습니다.");
        if (entry.preparationTags().contains("cured") && !compact.matches(".*(햄|베이컨|염지|cured|ham|bacon).*"))
            differences.add("염지·가공한 원료의 실험입니다. 실제 재료의 가공 상태를 확인해 주세요.");
        if (!fatMatches(compact, entry)) {
            differences.add("입력한 지방 비율이 이 실험의 지방 함량 구간에 들어가지 않습니다.");
            canEstimate = false;
        }
        if (!entry.source().statisticNote().isBlank()) differences.add(entry.source().statisticNote());
        if (reasons.isEmpty()) reasons.add("식품명과 조리 설명이 가까운 검색 후보입니다.");
        return new Assessment(List.copyOf(reasons), List.copyOf(differences), canEstimate, exact);
    }

    private static boolean fatMatches(String query, MeasuredYieldCatalog.Entry entry) {
        var requested = fatRange(query);
        if (requested == null) return true;
        String source = entry.source().sourceDescription().toLowerCase(Locale.ROOT);
        double lower = entry.species().equals("beef") ? 12 : 10;
        double upper = entry.species().equals("beef") ? 22 : 27;
        if (source.contains("low fat")) return new FatRange(0, true, lower, false).contains(requested);
        if (source.contains("medium fat")) return new FatRange(lower, true, upper, true).contains(requested);
        if (source.contains("high fat")) return new FatRange(upper, false, 100, true).contains(requested);
        // A record without a fat bracket cannot establish the requested numeric condition.
        return false;
    }

    private record FatRange(double lower, boolean lowerInclusive, double upper, boolean upperInclusive) {
        boolean contains(FatRange other) {
            return other.lower >= 0 && other.upper <= 100 && other.lower <= other.upper
                    && (other.lower > lower || other.lower == lower && (lowerInclusive || !other.lowerInclusive))
                    && (other.upper < upper || other.upper == upper && (upperInclusive || !other.upperInclusive));
        }
    }

    private static FatRange fatRange(String query) {
        if (!query.contains("지방") && !query.contains("fat")) return null;
        var range = Pattern.compile("([0-9]+(?:\\.[0-9]+)?)%?[~–-]([0-9]+(?:\\.[0-9]+)?)%").matcher(query);
        if (range.find()) return new FatRange(Double.parseDouble(range.group(1)), true, Double.parseDouble(range.group(2)), true);
        var point = Pattern.compile("([0-9]+(?:\\.[0-9]+)?)%").matcher(query);
        if (!point.find()) return null;
        double value = Double.parseDouble(point.group(1));
        if (query.contains("미만") || query.contains("<") && !query.contains("<=")) return new FatRange(0, true, value, false);
        if (query.contains("이하") || query.contains("<=")) return new FatRange(0, true, value, true);
        if (query.contains("초과") || query.contains(">") && !query.contains(">=")) return new FatRange(value, false, 100, true);
        if (query.contains("이상") || query.contains(">=")) return new FatRange(value, true, 100, true);
        return new FatRange(value, true, value, true);
    }

    private boolean methodMatches(MeasuredYieldCatalog.Entry entry) {
        String value = MeasuredYieldCatalog.key(method);
        if (entry.methods().contains(value)) return true;
        if (Set.of("구이", "굽기", "구운", "구워먹기").contains(value))
            return Set.of("roast", "grill", "dry_pan", "pan_fry").contains(entry.methodKey());
        if (Set.of("오븐", "오븐에굽기", "roast", "roasting", "bake", "baking").contains(value))
            return entry.methodKey().equals("roast");
        if (Set.of("팬구이", "팬에굽기", "panfry", "panfried", "panbroil").contains(value))
            return Set.of("dry_pan", "pan_fry").contains(entry.methodKey());
        if (Set.of("삶기", "삶은것", "simmer", "boil", "boiling").contains(value))
            return entry.methodKey().equals("simmer");
        if (Set.of("볶기", "볶음", "볶은것", "saute", "sauté", "stirfry").contains(value))
            return entry.methodKey().equals("saute");
        if (Set.of("그릴", "grill", "grilled", "grilling", "broil", "broiled").contains(value))
            return entry.methodKey().equals("grill");
        if (Set.of("조림", "브레이징", "braise", "braised", "braising").contains(value))
            return entry.methodKey().equals("braise");
        return false;
    }
}
