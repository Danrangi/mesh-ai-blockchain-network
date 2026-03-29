import 'package:flutter/material.dart';

class PeerChip extends StatelessWidget {
  final Map<String, dynamic> peer;

  const PeerChip({super.key, required this.peer});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(right: 8),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      decoration: BoxDecoration(
        color: const Color(0xFF1E2A1E),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.greenAccent.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const CircleAvatar(
            radius: 8,
            backgroundColor: Colors.greenAccent,
            child: Icon(Icons.person, size: 10, color: Colors.black),
          ),
          const SizedBox(width: 6),
          Text(
            peer['node_name'] ?? 'Unknown',
            style: const TextStyle(color: Colors.white70, fontSize: 12),
          ),
        ],
      ),
    );
  }
}
