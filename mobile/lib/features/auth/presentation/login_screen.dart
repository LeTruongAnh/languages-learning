import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme.dart';
import 'auth_controller.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  bool _loading = false;
  bool _registerMode = false;
  bool _showPassword = false;
  String? _error;

  static final _emailRe = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');

  @override
  void dispose() {
    for (final c in [_name, _email, _password, _confirm]) {
      c.dispose();
    }
    super.dispose();
  }

  /// Client-side validation — catches mistakes before a round-trip.
  String? _validate() {
    final email = _email.text.trim();
    if (email.isEmpty || _password.text.isEmpty) {
      return 'Nhập email và mật khẩu';
    }
    if (!_emailRe.hasMatch(email)) return 'Email không đúng định dạng';
    if (_registerMode) {
      if (_password.text.length < 8) return 'Mật khẩu tối thiểu 8 ký tự';
      if (_password.text != _confirm.text) return 'Mật khẩu nhập lại không khớp';
    }
    return null;
  }

  Future<void> _submit() async {
    final invalid = _validate();
    if (invalid != null) {
      setState(() => _error = invalid);
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    final controller = ref.read(authControllerProvider.notifier);
    final name = _name.text.trim();
    final error = _registerMode
        ? await controller.register(
            _email.text, _password.text, name.isEmpty ? null : name)
        : await controller.login(_email.text, _password.text);
    if (!mounted) return;
    setState(() {
      _loading = false;
      _error = error;
    });
    // On success the router redirects to /home automatically; a brand-new
    // account has no enrollments, so Home opens the language picker.
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 440),
            child: ListView(
              shrinkWrap: true,
              padding: const EdgeInsets.symmetric(horizontal: 28),
              children: [
                const Text('📚',
                    textAlign: TextAlign.center, style: TextStyle(fontSize: 40)),
                const SizedBox(height: 8),
                const Text('Vocab',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800)),
                const Text('Học từ vựng mỗi ngày, theo cách của bạn',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 14, color: AppColors.textSub)),
                const SizedBox(height: 28),
                if (_registerMode) ...[
                  TextField(
                    controller: _name,
                    textCapitalization: TextCapitalization.words,
                    decoration: const InputDecoration(
                        hintText: 'Tên hiển thị (tùy chọn)'),
                  ),
                  const SizedBox(height: 12),
                ],
                TextField(
                  controller: _email,
                  keyboardType: TextInputType.emailAddress,
                  autocorrect: false,
                  decoration: const InputDecoration(hintText: 'Email'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _password,
                  obscureText: !_showPassword,
                  onSubmitted: _registerMode ? null : (_) => _submit(),
                  decoration: InputDecoration(
                    hintText: 'Mật khẩu',
                    suffixIcon: IconButton(
                      icon: Icon(
                          _showPassword
                              ? Icons.visibility_off_outlined
                              : Icons.visibility_outlined,
                          size: 20,
                          color: AppColors.textSub),
                      onPressed: () =>
                          setState(() => _showPassword = !_showPassword),
                    ),
                  ),
                ),
                if (_registerMode) ...[
                  const Padding(
                    padding: EdgeInsets.only(top: 4, left: 4),
                    child: Text('Tối thiểu 8 ký tự',
                        style:
                            TextStyle(fontSize: 12, color: AppColors.textSub)),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _confirm,
                    obscureText: !_showPassword,
                    onSubmitted: (_) => _submit(),
                    decoration:
                        const InputDecoration(hintText: 'Nhập lại mật khẩu'),
                  ),
                ],
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(_error!,
                      textAlign: TextAlign.center,
                      style:
                          const TextStyle(color: AppColors.fail, fontSize: 13)),
                ],
                const SizedBox(height: 20),
                FilledButton(
                  style:
                      FilledButton.styleFrom(backgroundColor: AppColors.english),
                  onPressed: _loading ? null : _submit,
                  child: _loading
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white))
                      : Text(_registerMode ? 'Tạo tài khoản' : 'Đăng nhập'),
                ),
                const SizedBox(height: 10),
                TextButton(
                  onPressed: _loading
                      ? null
                      : () => setState(() {
                            _registerMode = !_registerMode;
                            _error = null;
                          }),
                  child: Text(
                    _registerMode
                        ? 'Đã có tài khoản? Đăng nhập'
                        : 'Chưa có tài khoản? Đăng ký',
                    style: const TextStyle(color: AppColors.textSub),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
