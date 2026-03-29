import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  // Change this to your machine IP when testing on a real phone
  // For FlutLab web preview, use your Codespaces forwarded port URL
  static const String baseUrl = 'http://localhost:8000';

  final Duration _timeout = const Duration(seconds: 4);

  Future<Map<String, dynamic>> getStatus() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/status'))
          .timeout(_timeout);
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
    } catch (_) {}
    return {'node': {}, 'peers': [], 'peer_count': 0};
  }

  Future<List<dynamic>> getMessages() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/messages'))
          .timeout(_timeout);
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['messages'] ?? [];
      }
    } catch (_) {}
    return [];
  }

  Future<bool> sendMessage(String content, {String recipientId = 'broadcast'}) async {
    try {
      final response = await http
          .post(
            Uri.parse('$baseUrl/send/message'),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({
              'content': content,
              'recipient_id': recipientId,
            }),
          )
          .timeout(_timeout);
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<List<dynamic>> getPeers() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/peers'))
          .timeout(_timeout);
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['peers'] ?? [];
      }
    } catch (_) {}
    return [];
  }
}
