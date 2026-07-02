/// API DTOs — parsed from the backend's camelCase JSON.
library;

class Language {
  const Language({
    required this.id,
    required this.code,
    required this.name,
    required this.ttsLang,
    this.accentColor,
  });

  final String id;
  final String code;
  final String name;
  final String ttsLang;
  final String? accentColor;

  factory Language.fromJson(Map<String, dynamic> json) => Language(
        id: json['id'] as String,
        code: json['code'] as String,
        name: json['name'] as String,
        ttsLang: json['ttsLang'] as String,
        accentColor: json['accentColor'] as String?,
      );
}

class LanguageSummary {
  const LanguageSummary({
    required this.languageId,
    required this.code,
    required this.name,
    required this.ttsLang,
    required this.dueCount,
    required this.newCount,
    required this.vocabDueNew,
    required this.sentenceDueNew,
    required this.todayLearned,
    required this.dailyLimit,
    this.accentColor,
  });

  final String languageId;
  final String code;
  final String name;
  final String ttsLang;
  final String? accentColor;
  final int dueCount;
  final int newCount;
  final int vocabDueNew;
  final int sentenceDueNew;
  final int todayLearned;
  final int dailyLimit;

  factory LanguageSummary.fromJson(Map<String, dynamic> json) => LanguageSummary(
        languageId: json['languageId'] as String,
        code: json['code'] as String,
        name: json['name'] as String,
        ttsLang: json['ttsLang'] as String,
        accentColor: json['accentColor'] as String?,
        dueCount: json['dueCount'] as int,
        newCount: json['newCount'] as int,
        vocabDueNew: json['vocabDueNew'] as int,
        sentenceDueNew: json['sentenceDueNew'] as int,
        todayLearned: json['todayLearned'] as int,
        dailyLimit: json['dailyLimit'] as int,
      );
}

class TodaySummary {
  const TodaySummary({
    required this.todayLearned,
    required this.passCount,
    required this.failCount,
    required this.skipCount,
    required this.passRate,
    required this.streakDays,
    required this.dueToday,
    required this.hardItemsCount,
  });

  final int todayLearned;
  final int passCount;
  final int failCount;
  final int skipCount;
  final double passRate;
  final int streakDays;
  final int dueToday;
  final int hardItemsCount;

  factory TodaySummary.fromJson(Map<String, dynamic> json) => TodaySummary(
        todayLearned: json['todayLearned'] as int,
        passCount: json['passCount'] as int,
        failCount: json['failCount'] as int,
        skipCount: json['skipCount'] as int,
        passRate: (json['passRate'] as num).toDouble(),
        streakDays: json['streakDays'] as int,
        dueToday: json['dueToday'] as int,
        hardItemsCount: json['hardItemsCount'] as int,
      );
}

class StudyItemModel {
  const StudyItemModel({
    required this.id,
    required this.itemType,
    required this.text,
    required this.hardLevel,
    required this.timesReview,
    this.pronunciation,
    this.vietnameseMeaning,
    this.example,
    this.exampleVietnamese,
  });

  final String id;
  final String itemType; // VOCABULARY | SENTENCE
  final String text;
  final String? pronunciation;
  final String? vietnameseMeaning;
  final String? example;
  final String? exampleVietnamese;
  final String hardLevel;
  final int timesReview;

  factory StudyItemModel.fromJson(Map<String, dynamic> json) => StudyItemModel(
        id: json['id'] as String,
        itemType: json['itemType'] as String,
        text: json['text'] as String,
        pronunciation: json['pronunciation'] as String?,
        vietnameseMeaning: json['vietnameseMeaning'] as String?,
        example: json['example'] as String?,
        exampleVietnamese: json['exampleVietnamese'] as String?,
        hardLevel: json['hardLevel'] as String,
        timesReview: json['timesReview'] as int,
      );
}

class SessionItem {
  const SessionItem({
    required this.id,
    required this.position,
    required this.plannedBucket,
    required this.item,
    this.result,
  });

  final String id;
  final int position;
  final String plannedBucket;
  final String? result;
  final StudyItemModel item;

  bool get isReview => plannedBucket.endsWith('REVIEW');

  factory SessionItem.fromJson(Map<String, dynamic> json) => SessionItem(
        id: json['id'] as String,
        position: json['position'] as int,
        plannedBucket: json['plannedBucket'] as String,
        result: json['result'] as String?,
        item: StudyItemModel.fromJson(json['item'] as Map<String, dynamic>),
      );
}

class StudySession {
  const StudySession({
    required this.id,
    required this.sessionType,
    required this.status,
    required this.totalItems,
    required this.completedItems,
    required this.passCount,
    required this.failCount,
    required this.skipCount,
    required this.items,
    this.languageId,
  });

  final String id;
  final String? languageId;
  final String sessionType;
  final String status;
  final int totalItems;
  final int completedItems;
  final int passCount;
  final int failCount;
  final int skipCount;
  final List<SessionItem> items;

  StudySession copyWith({
    int? completedItems,
    int? passCount,
    int? failCount,
    int? skipCount,
    String? status,
  }) =>
      StudySession(
        id: id,
        languageId: languageId,
        sessionType: sessionType,
        status: status ?? this.status,
        totalItems: totalItems,
        completedItems: completedItems ?? this.completedItems,
        passCount: passCount ?? this.passCount,
        failCount: failCount ?? this.failCount,
        skipCount: skipCount ?? this.skipCount,
        items: items,
      );

  factory StudySession.fromJson(Map<String, dynamic> json) => StudySession(
        id: json['id'] as String,
        languageId: json['languageId'] as String?,
        sessionType: json['sessionType'] as String,
        status: json['status'] as String,
        totalItems: json['totalItems'] as int,
        completedItems: json['completedItems'] as int,
        passCount: json['passCount'] as int,
        failCount: json['failCount'] as int,
        skipCount: json['skipCount'] as int,
        items: (json['items'] as List<dynamic>? ?? [])
            .map((e) => SessionItem.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class UserSettings {
  const UserSettings({
    required this.autoSpeakOnCardOpen,
    required this.speakExample,
    required this.speechRate,
    required this.speechVolume,
    required this.timezone,
  });

  final bool autoSpeakOnCardOpen;
  final bool speakExample;
  final double speechRate;
  final double speechVolume;
  final String timezone;

  factory UserSettings.fromJson(Map<String, dynamic> json) => UserSettings(
        autoSpeakOnCardOpen: json['autoSpeakOnCardOpen'] as bool,
        speakExample: json['speakExample'] as bool,
        speechRate: double.parse(json['speechRate'].toString()),
        speechVolume: double.parse(json['speechVolume'].toString()),
        timezone: json['timezone'] as String,
      );
}
