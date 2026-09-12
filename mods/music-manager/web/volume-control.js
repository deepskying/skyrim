'use strict';
// Keep a local draft separate from the periodically published audio state.
class MusicVolumeControl {
  constructor(send, session = `${Date.now()}-${Math.random()}`, now = Date.now) {
    this.send = send; this.session = session; this.now = now; this.sequence = 0;
    this.value = .5; this.editing = false; this.dirty = false;
    this.requestId = ''; this.pending = false; this.sentAt = 0; this.error = '';
  }
  begin() { this.editing = true; }
  input(percent) {
    this.editing = true; this.dirty = true;
    this.value = Math.max(0, Math.min(100, Number(percent))) / 100;
    this.error = '';
  }
  flush() {
    if (!this.dirty) return;
    this.dirty = false; this.pending = true; this.sentAt = this.now();
    this.requestId = `${this.session}:${++this.sequence}`;
    this.send({value: this.value, requestId: this.requestId});
  }
  finish() { this.editing = false; this.flush(); }
  receive(value, requestId = '', error = '') {
    // Older acknowledgements must stay ignored even after the latest was seen.
    if (this.requestId && requestId !== this.requestId) return;
    this.pending = false; this.error = error;
    if (!this.editing && !this.dirty) this.value = value;
  }
  get percent() { return Math.round(this.value * 100); }
  get message() {
    return this.error || (this.pending && this.now() - this.sentAt > 5000 ? '音量尚未确认，请重试。' : '');
  }
}
if (typeof module !== 'undefined') module.exports = MusicVolumeControl;
