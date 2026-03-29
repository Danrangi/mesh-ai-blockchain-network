import 'dart:async';
import 'package:flutter/foundation.dart';
import '../services/api_service.dart';

class NodeProvider extends ChangeNotifier {
  final ApiService _api;

  Map<String, dynamic> nodeInfo = {};
  List<dynamic> peers = [];
  List<dynamic> messages = [];
  bool isConnected = false;
  bool isSending = false;

  Timer? _pollTimer;

  NodeProvider(this._api) {
    // Load immediately then poll every 3 seconds
    refresh();
    _pollTimer = Timer.periodic(const Duration(seconds: 3), (_) => refresh());
  }

  Future<void> refresh() async {
    final status = await _api.getStatus();
    final msgs = await _api.getMessages();

    nodeInfo = status['node'] ?? {};
    peers = status['peers'] ?? [];
    messages = msgs;
    isConnected = nodeInfo['node_name'] != null;

    notifyListeners();
  }

  Future<bool> sendMessage(String content) async {
    isSending = true;
    notifyListeners();

    final success = await _api.sendMessage(content);

    isSending = false;
    notifyListeners();

    if (success) await refresh();
    return success;
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }
}
