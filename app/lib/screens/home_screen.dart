import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/node_provider.dart';
import '../widgets/message_bubble.dart';
import '../widgets/peer_chip.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _send(NodeProvider provider) async {
    final content = _controller.text.trim();
    if (content.isEmpty) return;
    _controller.clear();
    final success = await provider.sendMessage(content);
    if (!success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Could not send. Is the mesh node running?'),
          backgroundColor: Colors.redAccent,
        ),
      );
    }
    _scrollToBottom();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<NodeProvider>(
      builder: (context, provider, _) {
        // Auto scroll when new messages arrive
        if (provider.messages.isNotEmpty) _scrollToBottom();

        return Scaffold(
          backgroundColor: const Color(0xFF0F0F0F),
          appBar: AppBar(
            backgroundColor: const Color(0xFF1A1A1A),
            title: Row(
              children: [
                Container(
                  width: 10,
                  height: 10,
                  decoration: BoxDecoration(
                    color: provider.isConnected
                        ? Colors.greenAccent
                        : Colors.redAccent,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 10),
                Text(
                  provider.nodeInfo['node_name'] ?? 'MeshNet',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                    fontSize: 18,
                  ),
                ),
              ],
            ),
            actions: [
              IconButton(
                icon: const Icon(Icons.refresh, color: Colors.white70),
                onPressed: provider.refresh,
              ),
            ],
          ),
          body: Column(
            children: [
              _buildStatusBar(provider),
              _buildPeerRow(provider),
              const Divider(height: 1, color: Color(0xFF2A2A2A)),
              Expanded(child: _buildMessages(provider)),
              _buildInput(provider),
            ],
          ),
        );
      },
    );
  }

  Widget _buildStatusBar(NodeProvider provider) {
    return Container(
      color: const Color(0xFF1A1A1A),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: Row(
        children: [
          const Icon(Icons.hub, size: 13, color: Colors.white38),
          const SizedBox(width: 6),
          Text(
            '${provider.peers.length} peer${provider.peers.length == 1 ? '' : 's'} connected',
            style: const TextStyle(color: Colors.white54, fontSize: 12),
          ),
          const Spacer(),
          Text(
            provider.nodeInfo['node_id'] != null
                ? 'ID: ${provider.nodeInfo['node_id'].toString().substring(0, 8)}...'
                : 'Connecting...',
            style: const TextStyle(color: Colors.white30, fontSize: 11),
          ),
        ],
      ),
    );
  }

  Widget _buildPeerRow(NodeProvider provider) {
    if (provider.peers.isEmpty) {
      return Container(
        color: const Color(0xFF141414),
        padding: const EdgeInsets.all(10),
        child: const Row(
          children: [
            Icon(Icons.wifi_off, size: 13, color: Colors.white24),
            SizedBox(width: 8),
            Text(
              'Searching for nearby peers...',
              style: TextStyle(color: Colors.white30, fontSize: 12),
            ),
          ],
        ),
      );
    }

    return Container(
      color: const Color(0xFF141414),
      height: 56,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        itemCount: provider.peers.length,
        itemBuilder: (_, i) => PeerChip(peer: provider.peers[i]),
      ),
    );
  }

  Widget _buildMessages(NodeProvider provider) {
    if (provider.messages.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.chat_bubble_outline, size: 44, color: Colors.white12),
            SizedBox(height: 12),
            Text(
              'No messages yet.\nSend one to get started.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white24, fontSize: 14, height: 1.6),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      itemCount: provider.messages.length,
      itemBuilder: (_, i) {
        final msg = provider.messages[i];
        final isOwn = msg['sender_id'] == provider.nodeInfo['node_id'];
        return MessageBubble(message: msg, isOwn: isOwn);
      },
    );
  }

  Widget _buildInput(NodeProvider provider) {
    return Container(
      color: const Color(0xFF1A1A1A),
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 20),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _controller,
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                hintText: 'Type a message...',
                hintStyle: const TextStyle(color: Colors.white30),
                filled: true,
                fillColor: const Color(0xFF2A2A2A),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(24),
                  borderSide: BorderSide.none,
                ),
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 12,
                ),
              ),
              onSubmitted: (_) => _send(provider),
            ),
          ),
          const SizedBox(width: 8),
          GestureDetector(
            onTap: provider.isSending ? null : () => _send(provider),
            child: Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: provider.isSending
                    ? Colors.white12
                    : const Color(0xFF1A73E8),
                shape: BoxShape.circle,
              ),
              child: Icon(
                provider.isSending ? Icons.hourglass_empty : Icons.send,
                color: Colors.white,
                size: 20,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
